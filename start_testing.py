import json
import logging
import os
import asyncio
import httpx
import time
from datetime import datetime
import pandas as pd

logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  
    datefmt="%Y-%m-%d %H:%M:%S" 
)
current_file = os.path.splitext(os.path.basename(__file__))[0]
logger = logging.getLogger(current_file)



def load_config(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        config = json.load(file)
    return config

async def process_model(client, model, prompt, file_name, save_folder,):
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
        record["elapsed_time"] = time.time() - start_time  
        record['prompt_token_len'] = result['usage']['prompt_tokens']
        record['decode_token_len'] = result['usage']['completion_tokens']
        record["response"] = result['choices'][0]['message']
    except Exception as e:
        record["elapsed_time"] = time.time() - start_time
        record["error"] = str(e)
        logger.error(f"Error processing model {model['name']} for file {file_name}: {e}")
        return e, -1, -1, -1
    
    # save res to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_file_name = f"{os.path.basename(model['name'])}_{timestamp}.json"
    model_file_path = os.path.join(save_folder, model_file_name)
    with open(model_file_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=4, ensure_ascii=False)
    # logger.info(f"Prompt {file_name} for model {model['name']} successfully processed")
    return record['response'], record['prompt_token_len'], record['decode_token_len'], record['elapsed_time']

async def process_file(load_path, file_name, models, save_path, eval_dict):
    file_path = os.path.join(load_path, file_name)

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    prompt = json.loads(content)
    assert isinstance(prompt, list), "Error: 'prompt' must be a list."

    # save path
    prompt_name = os.path.splitext(file_name)[0]  
    save_folder = os.path.join(save_path, prompt_name)
    os.makedirs(save_folder, exist_ok=True)

    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [process_model(client, model, prompt, file_name, save_folder) for model in models]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    eval = []  
    for idx, result in enumerate(results):
        if result:
            response, prompt_token_len, decode_token_len, elapsed_time = result
            # print(f"Model: {models[idx]['name']}, Model_URL: {models[idx]['url']} Response: {result}")
            eval.append({'model': models[idx]['name'], 'response': response, 'prompt_token_len': prompt_token_len, 'decode_token_len': decode_token_len, 'elapsed_time': elapsed_time})
        else:
            print(f"Model: {models[idx]['name']}, Model_URL: {models[idx]['url']} Response: Error occurred")
    eval_dict[file_name] = eval

async def main(load_path, file_list, models, save_path, eval_dict):
    tasks = [process_file(load_path, file_name, models, save_path, eval_dict) for file_name in file_list]
    await asyncio.gather(*tasks)

def evaluate(eval_dict):
    return NotImplementedError

def summary_table(eval_dict, save_path):
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


if __name__ == "__main__":
    config_file = "config.json"
    config = load_config(config_file)
    
    model_count = config.get("model_count", 0)
    load_path = config.get("load_path", "")
    save_path = config.get("save_path", "")
    models = config.get("models", [])

    # baseline_model = {"name": "deepseek-chat", "url": "https://api.deepseek.com", "api_key": "sk-c4a8fe52693a4aaab64e648c42f40be6"}
    # models.append(baseline_model)

    logger.info(f"-------------------config information--------------------------")
    
    logger.info(f"model_count: {model_count}")
    logger.info(f"load_path: {load_path}")
    logger.info(f"save_path: {save_path}")
    for model in models:
        logger.info(f"model_name: {model['name']}, model_url: {model['url']}")
    logger.info(f"-------------------config information end--------------------------")
    file_list = [f for f in os.listdir(load_path) if os.path.isfile(os.path.join(load_path, f))]

    eval_dict = {}
    asyncio.run(main(load_path, file_list, models, save_path, eval_dict))
    print("Eval_dict:", eval_dict)
    summary_table(eval_dict, save_path)

