import json
import logging
import os
import asyncio
import httpx
import time
from datetime import datetime
import pandas as pd
import aiohttp
import sys
import copy

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.file_helper import *
from gpu_monitor import *

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
current_file = os.path.splitext(os.path.basename(__file__))[0]
logger = logging.getLogger(current_file)

# RUNNING RELATED
async def process_model(client, model_idx, model, prompt, test_name, image_path_list, save_folder, save_response, model_config):

    start_time = time.time()
    current_prompt = copy.deepcopy(prompt)
    for image_path in image_path_list:
        current_prompt[0]['content'].append({"type": "image_url", "image_url": {"url": "file://" + image_path}})
    record = {
        "test": test_name,
        "model": model['name'],
        'model_url': model['url'],
        "start_time": datetime.now().isoformat(),
        "prompt": current_prompt
    }

    config = {"model": model['name'], "messages": current_prompt}
    config.update(model_config)
    api_key = model['api_key'] if 'api_key' in model else 'token-123'
    try:
        response = await client.post(
            f"{model['url']}/v1/chat/completions",
            json=config,
            headers={"Authorization": f"Bearer {api_key}"}
        )
        response.raise_for_status()
        result = response.json()
        record['end_time'] = datetime.now().isoformat()
        start_time_datetime = datetime.fromisoformat(record['start_time'])
        end_time_datetime = datetime.fromisoformat(record['end_time'])
        record["elapsed_time"] = (end_time_datetime - start_time_datetime).total_seconds()
        record['prompt_token_len'] = result['usage']['prompt_tokens']
        record['decode_token_len'] = result['usage']['completion_tokens']
        record["response"] = result['choices'][0]['message']
    except httpx.HTTPError as http_error:
        # record["error"] = f"HTTPError: {http_error}, response content: {http_error.response.content if http_error.response else 'No Response'}"
        logger.error(f"HTTPError processing model {model['name']} for file {test_name}: {http_error}")
        return http_error, -1, -1, -1, -1, -1
    except Exception as e:
        record["elapsed_time"] = time.time() - start_time
        record["error"] = str(e)
        logger.error(f"Error processing model {model['name']} for file {test_name}: {e}")
        return e, -1, -1, -1, -1, -1

    # save res to file
    if save_response is True:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{model_idx}"
        normalized_path = model['name'].rstrip("/")
        model_file_name = f"{os.path.basename(normalized_path)}_{timestamp}.json"
        model_file_path = os.path.join(save_folder, model_file_name)
        with open(model_file_path, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=4, ensure_ascii=False)

    return record['response'], record['prompt_token_len'], record['decode_token_len'], record['elapsed_time'], record[
        'start_time'], record['end_time']


async def process_file(load_path, image_name, models, prompt, save_path, save_response, eval_dict, model_config):
    save_folder = ""
    image_path_list = [os.path.join(load_path, image_name),]
    test_name = image_name

    # save path
    if save_response is True:
        # test_name = os.path.splitext(test_name)[0]
        # test_name = image_name
        save_folder = os.path.join(save_path, test_name)
        os.makedirs(save_folder, exist_ok=True)

    async with httpx.AsyncClient(timeout=3000) as client:
        tasks = [
            process_model(client, model_idx, model, prompt, test_name, image_path_list, save_folder, save_response, model_config)
            for model_idx, model in enumerate(models)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    eval = []
    for idx, result in enumerate(results):
        if result:
            try:
                response, prompt_token_len, decode_token_len, elapsed_time, start_time, end_time = result
            except (ValueError, TypeError) as e:
                logger.error("Failed to unpack result:")
                logger.error(f"Result: {result}")
                logger.error(f"Error: {e}")
            
            eval.append(
                {
                    'model': models[idx]['name'],
                    'response': response,
                    'prompt_token_len': prompt_token_len,
                    'decode_token_len': decode_token_len,
                    'elapsed_time': elapsed_time,
                    "start_time": start_time,
                    "end_time": end_time,
                }
            )
        else:
            logger.warning(f"Model: {models[idx]['name']}, Model_URL: {models[idx]['url']} Response: Error occurred")
    eval_dict[test_name] = eval


async def main(load_path, image_list, models, prompt, save_path, save_response, eval_dict, model_config):
    tasks = [process_file(load_path, image_name, models, prompt, save_path, save_response, eval_dict, model_config) for image_name in image_list]
    await asyncio.gather(*tasks)


async def combined_run(load_path, image_list, models, prompt, save_path, save_response, eval_dict, model_config):
    stop_event = asyncio.Event()
    gpu_task = asyncio.create_task(gpu_main(models, save_path, stop_event))
    await main(load_path, image_list, models, prompt, save_path, save_response, eval_dict, model_config)
    stop_event.set()
    await gpu_task


# EVALUATION RELATED
def model_summary_table(
    eval_dict, save_path
):  # get the ealiest start time, the latest end time, total_prompt_num, total_decode_num, total_decode_speed for every model
    model_summary = {}

    for file, model_list in eval_dict.items():
        for record in model_list:
            model_name = record["model"]
            if record["start_time"] == -1:
                continue
            start_time = datetime.fromisoformat(record["start_time"])
            end_time = datetime.fromisoformat(record["end_time"])

            if model_name not in model_summary:
                model_summary[model_name] = {
                    "earliest_start": start_time,
                    "latest_end": end_time,
                    "total_prompt_num": record['prompt_token_len'],
                    "total_decode_num": record['decode_token_len'],
                    'latest_start': start_time,
                    'earliest_end': end_time
                }
            else:
                model_summary[model_name]["earliest_start"] = min(
                    model_summary[model_name]["earliest_start"], start_time
                )
                model_summary[model_name]["latest_end"] = max(model_summary[model_name]["latest_end"], end_time)
                # model_summary[model_name]["earliest_end"] = min(model_summary[model_name]["earliest_end"], end_time)
                # model_summary[model_name]["latest_start"] = max(model_summary[model_name]["latest_start"], start_time)
                model_summary[model_name]['total_prompt_num'] += record['prompt_token_len']
                model_summary[model_name]['total_decode_num'] += record['decode_token_len']

    for model_name, summary_item in model_summary.items():
        summary_item['total_runtime'] = (summary_item['latest_end'] - summary_item['earliest_start']).total_seconds()
        summary_item['decode_speed'] = summary_item['total_decode_num'] / summary_item['total_runtime'] if summary_item[
            "total_runtime"] > 0 else -1
        # print(model_name, summary_item['earliest_start'], summary_item['latest_start'], summary_item['earliest_end'], summary_item['latest_end'])

    data = []
    for model_name, summary_item in model_summary.items():
        data.append(
            {
                "Model": model_name,
                "Total Prompt Tokens": summary_item["total_prompt_num"],
                "Total Decode Tokens": summary_item["total_decode_num"],
                "Total Runtime (s)": round(summary_item["total_runtime"], 2),
                "Decode Speed (Tokens / s)": round(summary_item["decode_speed"], 2)
                if summary_item["decode_speed"] != -1 else -1
            }
        )

    df = pd.DataFrame(data)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"model_summary_table_{timestamp}.xlsx"
    output_file_path = os.path.join(save_path, file_name)

    df.to_excel(output_file_path, index=False)


def file_summary_table(eval_dict, save_path):
    data = []
    for prompt, entries in eval_dict.items():
        for entry in entries:
            data.append(
                {
                    'Prompt': prompt,
                    'Model': entry['model'],
                    'Prompt Token Length': entry['prompt_token_len'],
                    'Decode Token Length': entry['decode_token_len'],
                    'Elapsed Time(s)': entry['elapsed_time']
                }
            )

    df = pd.DataFrame(data)

    df['Decode Speed(Token / s)'] = df.apply(
        lambda row: round(row['Decode Token Length'] / row['Elapsed Time(s)'], 2)
        if row['Decode Token Length'] != -1 and row['Elapsed Time(s)'] > 0 else -1,
        axis=1
    )

    df['Elapsed Time(s)'] = df['Elapsed Time(s)'].apply(lambda x: round(x, 3) if x >= 0 else x)

    df_display = df.copy()
    df_display.loc[df_display.duplicated(subset=['Prompt']), 'Prompt'] = ''

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"file_summary_table_{timestamp}.xlsx"

    output_file_path = os.path.join(save_path, file_name)
    df_display.to_excel(output_file_path, index=False)


def response_table(eval_dict, save_path):
    result = {}

    for image_name, value_list in eval_dict.items():
        for item in value_list:
            model = item['model']
            response = item['response']

            if model not in result:
                result[model] = []

            result[model].append({image_name: response})

    os.makedirs(save_path, exist_ok=True)
    for model, responses in result.items():
        model_path = os.path.join(save_path, model)
        os.makedirs(model_path, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = os.path.join(model_path, f'response_table_{model}_{timestamp}.csv')

        data = []
        for response in responses:
            for key, value in response.items():
                data.append({'image_name': key, 'response': value})
        df = pd.DataFrame(data)
        df.to_csv(csv_file, index=False, encoding='utf-8')

    return result


def evaluate(eval_dict):
    return NotImplementedError


if __name__ == "__main__":
    config_file = "config_vlm_2.json"
    with open(config_file, 'r', encoding='utf-8') as file:
        config = json.load(file)

    load_path = config.get("load_images_path", "")
    load_prompt_path = config.get("load_prompt_path", "")
    save_path = config.get("save_path", "")
    save_response = config.get("save_response", True)
    model_config = config.get("model_config", {})
    models = config.get("models", [])

    os.makedirs(save_path, exist_ok=True)

    logger.info(f"-------------------config information--------------------------")

    logger.info(f"model_count: {len(models)}")
    logger.info(f"load_path: {load_path}")
    logger.info(f"save_path: {save_path}")
    logger.info(f"save_response: {save_response}")

    gpu_monitor = False
    for model in models:
        if 'gpu_url' in model.keys():
            gpu_monitor = True
            logger.info(
                f"model_name: {model['name']}, model_url: {model['url']}, gpu_url: {model['gpu_url']}, gpu_interval: {model['gpu_interval']}"
            )
        else:
            logger.info(f"model_name: {model['name']}, model_url: {model['url']}")

    logger.info(f"-------------------config information end--------------------------")

    prompt = load_json_vlm_prompt(load_prompt_path)

    image_list = [f for f in os.listdir(load_path) if os.path.isfile(os.path.join(load_path, f))]

    eval_dict = {}
    gpu_monitor = True
    if gpu_monitor is True:
        asyncio.run(combined_run(load_path, image_list, models, prompt, save_path, save_response, eval_dict, model_config))
    else:
        asyncio.run(main(load_path, image_list, models, prompt, save_path, save_response, eval_dict, model_config))

    # print("Eval_dict:", eval_dict)
    file_summary_table(eval_dict, save_path)
    model_summary_table(eval_dict, save_path)
    response_table(eval_dict, save_path)
