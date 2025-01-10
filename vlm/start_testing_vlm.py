import json
import logging
import os
import asyncio
import httpx
import time
from datetime import datetime
import pandas as pd
import sys
import copy

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.file_helper import *
from utils.gpu_monitor import *
from utils.summary import *

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
current_file = os.path.splitext(os.path.basename(__file__))[0]
logger = logging.getLogger(current_file)

# RUNNING RELATED
async def process_model(client, model_idx, model, prompt, test_name, image_path_list, save_folder, save_response, model_config):
    # print("idx", model_idx, "model", model, "prompt", prompt, "test_name", test_name, "path_list", image_path_list, "save_folder", save_folder, "response", save_response, "config", model_config)
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
    if model_config is not None:
        # TODO model_config的验证
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


async def process_file(mode, load_path, test_name, models, save_path, save_response, eval_dict, model_config=None, prompt=None):
    save_folder = ""
    if mode == 1:
        image_path_list = [os.path.join(load_path, test_name),]
        assert prompt != None, "In mode == 1, prompt path must be provided by the user"

    elif mode == 0:
        image_path_list = []
        test_path = os.path.join(load_path, test_name)
        for item in os.listdir(test_path):
            item_path = os.path.join(test_path, item)

            if os.path.isfile(item_path) and item.endswith('.txt'): # prompt
                prompt = load_json_vlm_prompt(item_path)

            elif os.path.isdir(item_path): # images
                for image in os.listdir(item_path):
                    image_path = os.path.join(item_path, image)
                    if os.path.isfile(image_path):
                        image_path_list.append(os.path.abspath(image_path))

    # save path
    if save_response is True:
        test_name = os.path.splitext(test_name)[0]
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


async def main(mode, load_path, test_list, models, save_path, save_response, eval_dict, model_config=None, prompt=None):
    tasks = [process_file(mode, load_path, test_name, models, save_path, save_response, eval_dict, model_config, prompt) for test_name in test_list]
    await asyncio.gather(*tasks)


async def combined_run(mode, load_path, test_list, models, save_path, save_response, eval_dict, model_config=None, prompt=None):
    stop_event = asyncio.Event()
    gpu_task = asyncio.create_task(gpu_main(models, save_path, stop_event))
    await main(mode, load_path, test_list, models, save_path, save_response, eval_dict, model_config, prompt)
    stop_event.set()
    await gpu_task


if __name__ == "__main__":
    config_file = "config_vlm.json"
    config = load_json_file(config_file)

    prompt = None

    load_config = config.get("load_config", [])

    mode = load_config.get("mode", -1)
    if mode == 0: # load底下只有一个路径，既存在prompt也存在image
        load_path = load_config.get("load_path", "")
    elif mode == 1: # load底下存在一个image文件夹和一个prompt文件，每个prompt和image文件夹中的一个文件构成输入
        load_path = load_config.get("load_images_path", "")
        load_prompt_path = load_config.get("load_prompt_path", "")
        prompt = load_json_vlm_prompt(load_prompt_path)
    else:
        assert mode >= 0, "mode must be assigned"
        
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


    if mode == 1:
        test_list = [f for f in os.listdir(load_path) if os.path.isfile(os.path.join(load_path, f))]
    else:
        test_list = [f for f in os.listdir(load_path) if os.path.isdir(os.path.join(load_path, f))]

    eval_dict = {}
    # gpu_monitor = True
    if gpu_monitor is True:
        asyncio.run(combined_run(mode, load_path, test_list, models, save_path, save_response, eval_dict, model_config, prompt))
    else:
        asyncio.run(main(mode, load_path, test_list, models, save_path, save_response, eval_dict, model_config, prompt))

    # print("Eval_dict:", eval_dict)
    file_summary_table(eval_dict, save_path)
    model_summary_table(eval_dict, save_path)
    response_table(eval_dict, save_path)
