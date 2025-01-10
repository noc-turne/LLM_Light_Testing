from enum import Enum
import os
import logging
from openai import OpenAI
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.file_helper import *

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    datefmt="%Y-%m-%d %H:%M:%S"
)
current_file = os.path.splitext(os.path.basename(__file__))[0]
logger = logging.getLogger(current_file)

class UserPromptGenerator(Enum):
    preset = 1
    AI = 2
    user = 3

def generate_sys_prompt(identity, topic):
    if(identity == 'user'):
        sys_prompt = f"你是用户，你的身份是一名女大学生，请你针对话题'{topic}'进行对话，你的性格活泼开朗。"
    elif(identity == 'AI'):
        sys_prompt = f"你是AI，针对话题'{topic}'进行对话。"
    else:
        logger.error("Wrong Identity")
        sys_prompt = ""
    return {"role": "system", "content": sys_prompt}

def call_ai(messages, sys_prompt, model_url="http://14.103.16.79:11000/v1", model_name="llama-3.3-70B-instruct"):
    try:
        client = OpenAI(api_key="token-123", base_url=model_url)

        msg = messages[:]
        msg.insert(0, sys_prompt)

        response = client.chat.completions.create(
            model=model_name,
            messages=msg,
            temperature=0.7,
            top_p=0.8,
            max_tokens=512,
            extra_body={
                "repetition_penalty": 1.05,
            },
        )

        answer = response.choices[0].message.content
        return answer
    except Exception as e:
        logger.error(f"AI call failed: {e}")
        return "抱歉，我无法处理这个请求。"

def extend_tree(background_name, messages, topic_hist_list, extend_num, save_path):
    msg = messages[:]
    for _ in range(extend_num):
        user_prompt_text = call_ai(msg, generate_sys_prompt('user', topic_hist_list[-1]))
        user_prompt = {"role": "user", "content": user_prompt_text}
        msg.append(user_prompt)

        response_text = call_ai(msg, generate_sys_prompt("AI", topic_hist_list[-1]), model_url="http://14.103.16.79:11001/v1", model_name="Qwen25_72B_instruct")
        response = {"role": "assistant", "content": response_text}
        msg.append(response)

    file_name = background_name
    for topic in topic_hist_list:
        file_name += f"_{topic}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name += f"_{extend_num}_{timestamp}.txt"

    os.makedirs(save_path, exist_ok=True)
    file_path = os.path.join(save_path, file_name)
    with open(file_path, 'w', encoding="utf-8") as f:
        json.dump(msg, f, indent=4, ensure_ascii=False)
    logger.info(f"done {file_name}")

def process_topic(background_name, messages, topic, topic_chosen_list, save_path, expand_num, extend_num, user_prompt_generator, preset_user_prompt_dict):
    local_messages = messages[:]
    topic_hist_list = [topic]

    # Generate user prompt
    if user_prompt_generator == UserPromptGenerator.preset:
        assert preset_user_prompt_dict is not None, "Error: preset_user_prompt_dict is None"
        user_prompt_text = preset_user_prompt_dict[topic]
    elif user_prompt_generator == UserPromptGenerator.AI:
        user_prompt_text = call_ai(local_messages, generate_sys_prompt('user', topic))
    else:
        user_prompt_text = input(f"请输入针对话题'{topic}'的内容：")

    user_prompt = {"role": "user", "content": user_prompt_text}
    local_messages.append(user_prompt)

    # Get AI response
    response_text = call_ai(local_messages, generate_sys_prompt("AI", topic), model_url="http://14.103.16.79:11001/v1", model_name="Qwen25_72B_instruct")
    response = {"role": "assistant", "content": response_text}
    local_messages.append(response)

    # Continue DFS
    dfs_generate_tree(
        background_name=background_name,
        messages=local_messages,
        topic_hist_list=topic_hist_list,
        depth=1,
        topic_chosen_list=topic_chosen_list,
        save_path=save_path,
        expand_num=expand_num,
        extend_num=extend_num,
        user_prompt_generator=user_prompt_generator
    )

def dfs_generate_tree(background_name, messages, topic_hist_list, depth, topic_chosen_list, save_path, expand_num=2, extend_num=6, user_prompt_generator=UserPromptGenerator.AI, preset_user_prompt_dict=None):
    """Recursive DFS tree generation with parallel processing at the first layer.

    Args:
        background_name (str): 场景名称
        messages (list): 历史对话
        topic_hist_list (list): 当前探索位置之前的topic_list
        depth (int): 当前所在树的深度
        topic_chosen_list (list): 树拓展时可选的topic
        save_path (str): 保存路径
        expand_num (int, optional): 树拓展的轮数. Defaults to 2.
        extend_num (int, optional): 树延伸的轮数. Defaults to 6.
        user_prompt_generator (UserPromptGenerator, optional): user_prompt由谁来产生. Defaults to UserPromptGenerator.preset.
    """
    if depth == expand_num:
        extend_tree(background_name, messages, topic_hist_list, extend_num, save_path)
        return

    if depth == 0:
        # Parallelize the first layer
        with ThreadPoolExecutor(max_workers=min(10, len(topic_chosen_list))) as executor:
            futures = [
                executor.submit(
                    process_topic, 
                    background_name, 
                    messages, 
                    topic, 
                    topic_chosen_list, 
                    save_path, 
                    expand_num, 
                    extend_num, 
                    user_prompt_generator,
                    preset_user_prompt_dict
                )
                for topic in topic_chosen_list
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error processing topic: {e}")
    else:
        for topic in topic_chosen_list:
            topic_hist_list.append(topic)
            if user_prompt_generator == UserPromptGenerator.preset:
                assert preset_user_prompt_dict is not None, "Error: preset_user_prompt_dict is None"
                user_prompt_text = preset_user_prompt_dict[topic]
            elif user_prompt_generator == UserPromptGenerator.AI:
                user_prompt_text = call_ai(messages, generate_sys_prompt('user', topic))
            else:
                user_prompt_text = input(f"请输入针对话题'{topic}'的内容：")

            user_prompt = {"role": "user", "content": user_prompt_text}
            messages.append(user_prompt)

            response_text = call_ai(messages, generate_sys_prompt("AI", topic), model_url="http://14.103.16.79:11001/v1", model_name="Qwen25_72B_instruct")
            response = {"role": "assistant", "content": response_text}
            messages.append(response)

            dfs_generate_tree(
                background_name, 
                messages, 
                topic_hist_list, 
                depth + 1, 
                topic_chosen_list, 
                save_path, 
                expand_num, 
                extend_num, 
                user_prompt_generator,
                preset_user_prompt_dict
            )

            messages.pop()  # 移除 AI 的响应
            messages.pop()  # 移除用户的提示
            topic_hist_list.pop()

if __name__ == "__main__":

    config_file = "conversation_config.json"
    config = load_json_file(config_file)

    background_name = config.get("background_name", "")

    background_conversation_file = config.get("background_conversation_file", "")
    background_prompt = load_json_txt_prompt(background_conversation_file)

    topic_chosen_file = config.get("topic_chosen_file", "")
    topic_chosen_list = load_json_file(topic_chosen_file)
    assert isinstance(topic_chosen_list, list), "Error: 'topic_chosen_list' must be a list."

    save_path = config.get("save_path", "")

    user_prompt_generator = config.get("user_prompt_generator_type", "AI")
    preset_user_prompt_dict = None
    if user_prompt_generator.lower() == "user":
        user_prompt_generator_type = UserPromptGenerator.user
    elif user_prompt_generator.lower() == "preset":
        user_prompt_generator_type = UserPromptGenerator.preset

        preset_user_prompt_file = config.get("preset_user_prompt_file", "")
        preset_user_prompt_dict = load_json_file(preset_user_prompt_file)
        assert isinstance(preset_user_prompt_dict, dict), "Error: 'preset_user_prompt_dict' must be a dict"

        assert topic_chosen_list == preset_user_prompt_dict.keys(), "Error: topic_chosen_list != preset_user_prompt_dict.keys()"
    else:
        user_prompt_generator_type = UserPromptGenerator.AI

    dfs_generate_tree(
        background_name=background_name, 
        messages=background_prompt, 
        topic_hist_list=[], 
        depth=0, 
        topic_chosen_list=topic_chosen_list, 
        save_path=save_path, 
        expand_num=2, 
        extend_num=6, 
        user_prompt_generator=user_prompt_generator_type,
        preset_user_prompt_dict=preset_user_prompt_dict
    )
