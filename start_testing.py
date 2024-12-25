import json
import logging
import os
import asyncio
import httpx
import time
from datetime import datetime
import pandas as pd
import aiohttp

logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  
    datefmt="%Y-%m-%d %H:%M:%S" 
)
current_file = os.path.splitext(os.path.basename(__file__))[0]
logger = logging.getLogger(current_file)

# GPU RELATED
def gpu_info2txt(file_name, response):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(file_name, "a") as file:
        file.write(f"Current Time: {timestamp}\n")
        for gpu in response:
            file.write(f"GPU {gpu['gpu_id']} ({gpu['name']}):\n")
            file.write(f"  GPU Utilization: {gpu['gpu_utilization']}%\n")
            file.write(f"  Memory Utilization: {gpu['memory_utilization']}%\n")
            file.write(f"  Memory: {gpu['memory_used']} MiB / {gpu['memory_total']} MiB\n")
            file.write("\n")  
        file.write("\n")

async def fetch_gpu_info(api_url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Received status code {response.status} for URL {api_url}")
                    return None
        except Exception as e:
            logger.error(f"Failed to fetch GPU info from {api_url}. Exception: {e}")
            return None


async def monitor_gpu(api_url, interval, file_name, stop_event):
    while not stop_event.is_set():
        response = await fetch_gpu_info(api_url)
        if response:  # Ensure the response is valid
            gpu_info2txt(file_name, response)
        await asyncio.sleep(interval)

async def gpu_main(models, save_path, stop_event):
    tasks = []
    gpu_info_path = os.path.join(save_path, "gpu_info")
    os.makedirs(gpu_info_path, exist_ok=True)
    for idx, model in enumerate(models):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{idx}"
        if "gpu_url" not in model.keys():
            continue
        normalized_path = model['name'].rstrip("/")
        file_name = os.path.join(gpu_info_path, os.path.basename(normalized_path) + f"_{timestamp}.txt")
        tasks.append(monitor_gpu(model['gpu_url'] + "/gpu_info", interval=model['gpu_interval'], file_name=file_name, stop_event=stop_event))
        
    await asyncio.gather(*tasks)


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
    return record['response'], record['prompt_token_len'], record['decode_token_len'], record['elapsed_time'], record['start_time'], record['end_time']

async def process_file(load_path, file_name, models, save_path, save_response, eval_dict):
    file_path = os.path.join(load_path, file_name)

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    try:
        prompt = json.loads(content)
        assert isinstance(prompt, list), "Error: 'prompt' must be a list."
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON in file: {file_name}")
        print(f"Error: {e}")
        return

    save_folder = ""
    # save path
    if save_response is True:
        prompt_name = os.path.splitext(file_name)[0]  
        save_folder = os.path.join(save_path, prompt_name)
        os.makedirs(save_folder, exist_ok=True)

    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [process_model(client, model_idx, model, prompt, file_name, save_folder, save_response) for model_idx, model in enumerate(models)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    eval = []  
    for idx, result in enumerate(results):
        if result:
            response, prompt_token_len, decode_token_len, elapsed_time, start_time, end_time = result
            eval.append({'model': models[idx]['name'], 'response': response, 'prompt_token_len': prompt_token_len, 'decode_token_len': decode_token_len, 'elapsed_time': elapsed_time, "start_time": start_time, "end_time": end_time})
        else:
            print(f"Model: {models[idx]['name']}, Model_URL: {models[idx]['url']} Response: Error occurred")
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


# EVALUATION RELATED
def model_summary_table(eval_dict, save_path): # get the ealiest start time, the latest end time, total_prompt_num, total_decode_num, total_decode_speed for every model
    model_summary = {}

    for file, model_list in eval_dict.items():
        for record in model_list:
            model_name = record["model"]
            if record["start_time"] == -1:
                continue
            start_time = datetime.fromisoformat(record["start_time"])
            end_time = datetime.fromisoformat(record["end_time"])
            
            if model_name not in model_summary:
                model_summary[model_name] = {"earliest_start": start_time, "latest_end": end_time, "total_prompt_num": record['prompt_token_len'], "total_decode_num": record['decode_token_len'], 'latest_start': start_time, 'earliest_end': end_time}
            else:
                model_summary[model_name]["earliest_start"] = min(model_summary[model_name]["earliest_start"], start_time)
                model_summary[model_name]["latest_end"] = max(model_summary[model_name]["latest_end"], end_time)
                # model_summary[model_name]["earliest_end"] = min(model_summary[model_name]["earliest_end"], end_time)
                # model_summary[model_name]["latest_start"] = max(model_summary[model_name]["latest_start"], start_time)
                model_summary[model_name]['total_prompt_num'] += record['prompt_token_len']
                model_summary[model_name]['total_decode_num'] += record['decode_token_len']

    for model_name, summary_item in model_summary.items():
        summary_item['total_runtime'] = (summary_item['latest_end'] - summary_item['earliest_start']).total_seconds()
        summary_item['decode_speed'] = summary_item['total_decode_num'] / summary_item['total_runtime'] if summary_item["total_runtime"] > 0 else -1
        # print(model_name, summary_item['earliest_start'], summary_item['latest_start'], summary_item['earliest_end'], summary_item['latest_end'])

    data = []
    for model_name, summary_item in model_summary.items():
        data.append({
            "Model": model_name,
            "Total Prompt Tokens": summary_item["total_prompt_num"],
            "Total Decode Tokens": summary_item["total_decode_num"],
            "Total Runtime (s)": round(summary_item["total_runtime"], 2),
            "Decode Speed (Tokens / s)": round(summary_item["decode_speed"], 2) if summary_item["decode_speed"] != -1 else -1
        })

    df = pd.DataFrame(data)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"model_summary_table_{timestamp}.xlsx"
    output_file_path = os.path.join(save_path, file_name)

    df.to_excel(output_file_path, index=False)



def file_summary_table(eval_dict, save_path):
    data = []
    for prompt, entries in eval_dict.items():
        for entry in entries:
            data.append({
                'Prompt': prompt,
                'Model': entry['model'],
                'Prompt Token Length': entry['prompt_token_len'],
                'Decode Token Length': entry['decode_token_len'],
                'Elapsed Time(s)': entry['elapsed_time']
            })

    df = pd.DataFrame(data)

    df['Decode Speed(Token / s)'] = df.apply(lambda row: round(row['Decode Token Length'] / row['Elapsed Time(s)'], 2) 
                                if row['Decode Token Length'] != -1 and row['Elapsed Time(s)'] > 0 else -1, axis=1)

    df['Elapsed Time(s)'] = df['Elapsed Time(s)'].apply(lambda x: round(x, 3) if x >= 0 else x)

    df_display = df.copy()
    df_display.loc[df_display.duplicated(subset=['Prompt']), 'Prompt'] = ''

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"summary_table_{timestamp}.xlsx"

    output_file_path = os.path.join(save_path, file_name)
    df_display.to_excel(output_file_path, index=False)

def evaluate(eval_dict):
    return NotImplementedError


if __name__ == "__main__":
    config_file = "config.json"
    with open(config_file, 'r', encoding='utf-8') as file:
        config = json.load(file)
    
    model_count = config.get("model_count", 0)
    load_path = config.get("load_path", "")
    save_path = config.get("save_path", "")
    save_response = config.get("save_response", True)
    models = config.get("models", [])

    logger.info(f"-------------------config information--------------------------")
    
    logger.info(f"model_count: {model_count}")
    logger.info(f"load_path: {load_path}")
    logger.info(f"save_path: {save_path}")
    logger.info(f"save_response: {save_response}")
    for model in models:
        if 'gpu_url' in model.keys():
            logger.info(f"model_name: {model['name']}, model_url: {model['url']}, gpu_url: {model['gpu_url']}, gpu_interval: {model['gpu_interval']}")
        else:
            logger.info(f"model_name: {model['name']}, model_url: {model['url']}")

    logger.info(f"-------------------config information end--------------------------")
    file_list = [f for f in os.listdir(load_path) if os.path.isfile(os.path.join(load_path, f))]

    eval_dict = {}
    asyncio.run(combined_run(load_path, file_list, models, save_path, eval_dict, save_response))

    # print("Eval_dict:", eval_dict)
    file_summary_table(eval_dict, save_path)
    model_summary_table(eval_dict, save_path)

