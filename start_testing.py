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

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
current_file = os.path.splitext(os.path.basename(__file__))[0]
logger = logging.getLogger(current_file)

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.file_helper import *
from utils.gpu_monitor import *
from utils.summary import *


# RUNNING RELATED
async def process_model(client, model_idx, model, prompt, file_name, save_folder, save_response):
    start_time = time.time()
    record = {
        "file": file_name,
        "model": model['name'],
        'model_url': model['url'],
        "start_time": datetime.now().isoformat(),
        "prompt": prompt
    }
    api_key = model['api_key'] if 'api_key' in model else 'token-123'
    try:
        response = await client.post(
            f"{model['url']}/v1/chat/completions",
            json={
                "model": model['name'],
                "messages": prompt
            },
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
        logger.error(f"HTTPError processing model {model['name']} for file {file_name}: {http_error}")
        return http_error, -1, -1, -1, -1, -1
    except Exception as e:
        record["elapsed_time"] = time.time() - start_time
        record["error"] = str(e)
        logger.error(f"Error processing model {model['name']} for file {file_name}: {e}")
        return e, -1, -1, -1, -1, -1

    # save res to file
    if save_response is True:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{model_idx}"
        normalized_path = model['name'].rstrip("/")
        model_file_name = f"{os.path.basename(normalized_path)}_{timestamp}.json"
        model_file_path = os.path.join(save_folder, model_file_name)
        with open(model_file_path, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=4, ensure_ascii=False)
    # logger.info(f"Prompt {file_name} for model {model['name']} successfully processed")
    return record['response'], record['prompt_token_len'], record['decode_token_len'], record['elapsed_time'], record[
        'start_time'], record['end_time']


async def process_file(load_path, file_name, models, save_path, save_response, eval_dict):
    file_path = os.path.join(load_path, file_name)

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    try:
        prompt = json.loads(content)
        assert isinstance(prompt, list), "Error: 'prompt' must be a list."
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON in file: {file_name}")
        logger.error(f"Error: {e}")
        return

    save_folder = ""
    # save path
    if save_response is True:
        prompt_name = os.path.splitext(file_name)[0]
        save_folder = os.path.join(save_path, prompt_name)
        os.makedirs(save_folder, exist_ok=True)

    async with httpx.AsyncClient(timeout=3000) as client:
        tasks = [
            process_model(client, model_idx, model, prompt, file_name, save_folder, save_response)
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
                    "end_time": end_time
                }
            )
        else:
            logger.warning(f"Model: {models[idx]['name']}, Model_URL: {models[idx]['url']} Response: Error occurred")
    eval_dict[file_name] = eval


async def main(load_path, file_list, models, save_path, save_response, eval_dict):
    tasks = [process_file(load_path, file_name, models, save_path, save_response, eval_dict) for file_name in file_list]
    await asyncio.gather(*tasks)


async def combined_run(load_path, file_list, models, save_path, eval_dict, save_response):
    stop_event = asyncio.Event()
    gpu_task = asyncio.create_task(gpu_main(models, save_path, stop_event))
    await main(load_path, file_list, models, save_path, save_response, eval_dict)
    stop_event.set()
    await gpu_task


if __name__ == "__main__":
    config_file = "config.json"
    with open(config_file, 'r', encoding='utf-8') as file:
        config = json.load(file)

    load_path = config.get("load_path", "")
    save_path = config.get("save_path", "")
    save_response = config.get("save_response", True)
    models = config.get("models", [])

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
    file_list = [f for f in os.listdir(load_path) if os.path.isfile(os.path.join(load_path, f))]

    eval_dict = {}
    asyncio.run(combined_run(load_path, file_list, models, save_path, eval_dict, save_response))

    # print("Eval_dict:", eval_dict)
    file_summary_table(eval_dict, save_path)
    model_summary_table(eval_dict, save_path)
