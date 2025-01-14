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

from utils.file_helper import *
from utils.gpu_monitor import *
from utils.summary import *

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
current_file = os.path.splitext(os.path.basename(__file__))[0]
logger = logging.getLogger(current_file)

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# RUNNING RELATED
async def process_model(client, model_idx, model, prompt, file_name, save_folder, save_response, model_config):
    """对模型发送具体请求

    Args:
        client (AsyncClient): 用于异步发送请求的client
        model_idx (int): model序号
        model (dict): config文件中某个model的config信息
        prompt (str): 询问的prompt
        file_name (str): 询问prompt的文件名, 用于保存回答信息
        save_folder (str): 模型保存路径
        save_response (bool): 是否需要保存具体回答
        model_config(dict): 模型请求时额外参数

    Returns:
        records: 用于评估的模型生成信息
    """
    start_time = time.time()
    record = {
        "file": file_name,
        "model": model['name'],
        'model_url': model['url'],
        "start_time": datetime.now().isoformat(),
        "prompt": prompt
    }
    api_key = model['api_key'] if 'api_key' in model else 'token-123'
    config = {"model": model['name'], "messages": prompt}
    if model_config is not None:
        config.update(model_config)
        print(config)
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
    return record['response'], record['prompt_token_len'], record['decode_token_len'], record['elapsed_time'], record[
        'start_time'], record['end_time']


async def process_file(load_path, file_name, models, save_path, save_response, eval_dict, model_config):
    """将单一file分配给多个模型并行处理

    Args:
        load_path (str): prompt加载路径
        file_name (str): prompt文件名
        models (list): config文件中的model信息
        save_path (str): 保存路径
        save_response (bool): 是否保存具体回答
        eval_dict (dict): 用于生成summary的字典,传入值为空
    """
    file_path = os.path.join(load_path, file_name)

    prompt = load_json_txt_prompt(file_path)

    save_folder = ""
    # save path
    if save_response is True:
        prompt_name = os.path.splitext(file_name)[0]
        save_folder = os.path.join(save_path, prompt_name)
        os.makedirs(save_folder, exist_ok=True)

    async with httpx.AsyncClient(timeout=36000) as client:
        tasks = [
            process_model(client, model_idx, model, prompt, file_name, save_folder, save_response, model_config)
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


async def main(load_path, file_list, models, save_path, save_response, eval_dict, model_config):
    tasks = [process_file(load_path, file_name, models, save_path, save_response, eval_dict, model_config) for file_name in file_list]
    await asyncio.gather(*tasks)


async def combined_run(load_path, file_list, models, save_path, eval_dict, save_response, model_config):
    stop_event = asyncio.Event()
    gpu_task = asyncio.create_task(gpu_main(models, save_path, stop_event))
    await main(load_path, file_list, models, save_path, save_response, eval_dict, model_config)
    stop_event.set()
    await gpu_task


if __name__ == "__main__":
    config_file = "config.json"
    config = load_json_file(config_file)

    load_path = config.get("load_path", "")
    save_path = config.get("save_path", "")
    save_response = config.get("save_response", True)
    summary_info = config.get("summary", {})
    model_config = config.get("model_config", {})
    flag, info = validate_model_config_params(model_config)
    if flag is False:
        logger.error(info)
        raise ConfigError

    models = config.get("models", [])

    logger.info(f"-------------------config information--------------------------")

    logger.info(f"model_count: {len(models)}")
    logger.info(f"load_path: {load_path}")
    logger.info(f"save_path: {save_path}")
    logger.info(f"save_response: {save_response}")
    logger.info(f"summary_info: {summary_info}" )
    logger.info(f"model_config: {model_config}")
    gpu_monitor = False
    for model in models:
        if 'gpu_url' in model.keys():
            gpu_monitor = True
            logger.info(
                f"model_name: {model['name']}, model_url: {model['url']}, gpu_url: {model['gpu_url']}, gpu_interval: {model.get('gpu_interval', 3)}"
            )
        else:
            logger.info(f"model_name: {model['name']}, model_url: {model['url']}")

    logger.info(f"-------------------config information end--------------------------")
    file_list = [f for f in os.listdir(load_path) if os.path.isfile(os.path.join(load_path, f))]

    eval_dict = {}

    if gpu_monitor is True:
        asyncio.run(combined_run(load_path, file_list, models, save_path, eval_dict, save_response, model_config))
    else:
        asyncio.run(main(load_path, file_list, models, save_path, eval_dict, save_response, model_config))

    if summary_info.get("model_summary", False) is True:
        model_summary_table(eval_dict, save_path)
    if summary_info.get("file_summary", False) is True:
        file_summary_table(eval_dict, save_path)
    if summary_info.get("response_summary", False) is True:
        response_table(eval_dict, save_path)

