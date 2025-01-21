from enum import Enum
import os
import logging
from openai import OpenAI
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import sys
import requests
from copy import deepcopy


SYSTEM_TEST = False # 测试将历史对话全放在system_prompt中

def test_message_in_system_prompt(messages, role_name="AI"):
    extracted_content = []
    for message in messages[:-1]:
        role = message.get("role", "unknown")
        if role == "assistant":
            role = role_name
        content = message.get("content", "")
        extracted_content.append(f"{role}: {content}")
    
    return "\n".join(extracted_content)

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

def cleans2s_generate(user_input, uid=None):
    url = "http://103.177.28.193:11000/process"

    request_data = {
        "user_input": user_input,
        "uid": uid  
    }

    try:
        response = requests.post(url, json=request_data)

        if response.status_code != 200:
            response.raise_for_status()

        response_data = response.json()
        outputs = response_data.get("outputs", "")
        uid = response_data.get("uid", "")
        return outputs, uid

    except requests.exceptions.RequestException as e:
        raise SystemExit(f"请求失败: {e}")


def generate_sys_prompt(identity, topic):
    if(identity == 'user'):
        sys_prompt = f"你是用户，你的身份是一名女大学生，请你针对话题'{topic}'进行对话，你的性格活泼开朗。"
    elif(identity == 'AI'):
        sys_prompt = f"你是AI，针对话题'{topic}'进行对话。"
    else:
        logger.error("Wrong Identity")
        sys_prompt = ""
    return {"role": "system", "content": sys_prompt}

def call_ai(messages, sys_prompt, model_url="http://14.103.16.79:11000/v1", model_name="llama-3.3-70B-instruct", uid=None):
    """调用AI, 需传入历史对话和system_prompt, 当model_name为"cleans2s"时, 调用cleans2s的接口

    Args:
        messages (_type_): _description_
        sys_prompt (_type_): _description_
        model_url (str, optional): _description_. Defaults to "http://14.103.16.79:11000/v1".
        model_name (str, optional): _description_. Defaults to "llama-3.3-70B-instruct".
        uid (_type_, optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
    if model_name.lower() == 'cleans2s':
        return cleans2s_generate(messages[-1]['content'], uid)
    else:  
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
            raise SystemExit(f"请求失败: {e}")


def process_topic(background_name, messages, topic, topic_chosen_list, save_path, expand_num, extend_num, user_prompt_generator, preset_user_prompt_dict, AI_response_model=None, uid=None):
    local_messages = messages[:]
    topic_hist_list = [topic]

    # Generate user prompt
    if user_prompt_generator == UserPromptGenerator.preset:
        assert preset_user_prompt_dict is not None, "Error: preset_user_prompt_dict is None"
        user_prompt_text = preset_user_prompt_dict[topic]
    elif user_prompt_generator == UserPromptGenerator.AI:
        if SYSTEM_TEST == True:
            system_prompt = generate_sys_prompt('user', topic)
            system_prompt['content'] += test_message_in_system_prompt(local_messages)
            user_prompt_text = call_ai([local_messages[-1]], system_prompt)
        else:
            user_prompt_text = call_ai(local_messages, generate_sys_prompt('user', topic))
    else:
        user_prompt_text = input(f"请输入针对话题'{topic}'的内容：")

    user_prompt = {"role": "user", "content": user_prompt_text}
    local_messages.append(user_prompt)

    # Get AI response
    if SYSTEM_TEST == True:
        system_prompt = generate_sys_prompt('AI', topic)
        system_prompt['content'] += test_message_in_system_prompt(local_messages)
        response_text = call_ai([local_messages[-1]], system_prompt, model_url="http://14.103.16.79:11001/v1", model_name="Qwen25_72B_instruct")
    else:
        if AI_response_model.lower() == 'llama':
            response_text = call_ai(local_messages, generate_sys_prompt("AI", topic))
        elif AI_response_model.lower() == 'qwen':
            response_text = call_ai(local_messages, generate_sys_prompt("AI", topic), model_url="http://14.103.16.79:11001/v1", model_name="Qwen25_72B_instruct")
        elif AI_response_model.lower() == 'cleans2s':
            response_text, uid = call_ai(local_messages, '', model_name='cleans2s', uid=uid)
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
        user_prompt_generator=user_prompt_generator,
        AI_response_model=AI_response_model,
        uid=uid
    )

    # 树的开始不需要回溯

def dfs_generate_tree(background_name, messages, topic_hist_list, depth, topic_chosen_list, save_path, expand_num=2, extend_num=6, user_prompt_generator=UserPromptGenerator.AI, preset_user_prompt_dict=None, AI_response_model=None, uid=None):
    """Recursive DFS tree generation with parallel processing at the first layer.
    user的回答由user_prompt_generator来决定如何生成,AI的回答必定由AI生成

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
        extend_tree(background_name, messages, topic_hist_list, extend_num, save_path, AI_response_model, uid)
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
                    preset_user_prompt_dict,
                    AI_response_model,
                    uid
                )
                for topic in topic_chosen_list
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error processing topic: {e}")
    else:
        local_msg = messages[:]
        for topic in topic_chosen_list:
            topic_hist_list.append(topic)

            # Generate user prompt
            if user_prompt_generator == UserPromptGenerator.preset:
                assert preset_user_prompt_dict is not None, "Error: preset_user_prompt_dict is None"
                user_prompt_text = preset_user_prompt_dict[topic]
            elif user_prompt_generator == UserPromptGenerator.AI:
                if SYSTEM_TEST == True:
                    system_prompt = generate_sys_prompt('user', topic)
                    system_prompt['content'] += test_message_in_system_prompt(local_msg)
                    user_prompt_text = call_ai([local_msg[-1]], system_prompt)
                else:
                    user_prompt_text = call_ai(local_msg, generate_sys_prompt('user', topic))
            else:
                user_prompt_text = input(f"请输入针对话题'{topic}'的内容：")

            user_prompt = {"role": "user", "content": user_prompt_text}
            local_msg.append(user_prompt)

            # Get AI response
            if SYSTEM_TEST == True:
                system_prompt = generate_sys_prompt('AI', topic)
                system_prompt['content'] += test_message_in_system_prompt(local_msg)
                response_text = call_ai([local_msg[-1]], system_prompt, model_url="http://14.103.16.79:11001/v1", model_name="Qwen25_72B_instruct")
            else:
                if AI_response_model.lower() == 'llama':
                    response_text = call_ai(local_msg, generate_sys_prompt("AI", topic))
                elif AI_response_model.lower() == 'qwen':
                    response_text = call_ai(local_msg, generate_sys_prompt("AI", topic), model_url="http://14.103.16.79:11001/v1", model_name="Qwen25_72B_instruct")
                elif AI_response_model.lower() == 'cleans2s':
                    response_text, uid = call_ai(local_msg, '', model_name='cleans2s', uid=uid)
                    
            response = {"role": "assistant", "content": response_text}
            local_msg.append(response)

            # Continue DFS
            dfs_generate_tree(
                background_name, 
                local_msg, 
                topic_hist_list, 
                depth + 1, 
                topic_chosen_list, 
                save_path, 
                expand_num, 
                extend_num, 
                user_prompt_generator,
                preset_user_prompt_dict,
                AI_response_model, 
                uid
            )

            local_msg.pop()  # 移除 AI 的响应
            local_msg.pop()  # 移除用户的提示
            topic_hist_list.pop()


def extend_tree(background_name, messages, topic_hist_list, extend_num, save_path, AI_response_model, uid):
    """AI自问自答,生成extend_num轮对话

    Args:
        background_name (str): 背景名,用于文件保存
        messages (list): 历史对话
        topic_hist_list (str): 历史话题, 用于文件保存
        extend_num (int): 对话轮数
        save_path (str): 保存路径
    """
    msg = messages[:]
    for _ in range(extend_num):
        user_prompt_text = call_ai(msg, generate_sys_prompt('user', topic_hist_list[-1]))
        user_prompt = {"role": "user", "content": user_prompt_text}
        msg.append(user_prompt)

        if AI_response_model.lower() == 'llama':
            response_text = call_ai(msg, generate_sys_prompt("AI", topic))
        elif AI_response_model.lower() == 'qwen':
            response_text = call_ai(msg, generate_sys_prompt("AI", topic), model_url="http://14.103.16.79:11001/v1", model_name="Qwen25_72B_instruct")
        elif AI_response_model.lower() == 'cleans2s':
            response_text, uid = call_ai(msg, '', model_name='cleans2s', uid=uid)
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

    AI_response_model = config.get("AI_response_model", '')

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
        preset_user_prompt_dict=preset_user_prompt_dict,
        AI_response_model = AI_response_model
    )
