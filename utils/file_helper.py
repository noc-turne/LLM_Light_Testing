import json
import logging
import os

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    datefmt="%Y-%m-%d %H:%M:%S"
)
current_file = os.path.splitext(os.path.basename(__file__))[0]
logger = logging.getLogger(current_file)


def load_json_file(load_path) -> json:
    """load json file

    Args:
        load_path (str): path

    Raises:
        json.JSONDecodeError: 

    Returns:
        json: json format
    """
    with open(load_path, 'r', encoding='utf-8') as file:
        content = file.read()
    try:
        json_content = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON in file: {load_path}")
        logger.error(f"Error: {e}")
        raise json.JSONDecodeError
    
    return json_content


def load_json_txt_prompt(load_path, role='user') -> list:
    """load json txt prompt, if not in json format, automatically transform txt into json

    Args:
        load_path (str): path
        role(str): role of the prompt

    Returns:
        list: prompt, an example is         
        prompt = [
            {
                "role": role,
                "content": content
            }
        ]
    """

    with open(load_path, 'r', encoding='utf-8') as file:
        content = file.read()
    try:
        prompt = json.loads(content)
        assert isinstance(prompt, list), "Error: 'prompt' must be a list."
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON in file: {load_path}")
        logger.error(f"Error: {e}")
        logger.warning(f"Automatically transform txt into json")
        prompt = [
            {
                "role": role,
                "content": content
            }
        ]
        logger.warning(f"The formated json prompt is shown below:\n{prompt}")
    
    return prompt


def load_json_vlm_prompt(load_path, role='user') -> list:
    """load json vlm prompt, if not in json format, automatically transform txt into json

    Args:
        load_path (str): path
        role(str): role of the prompt

    Returns:
        list: prompt, an example is         
        prompt = [
            {
                "role": role,
                "content": [
                    {
                        "type": "text",
                        "text": content
                    }
                ]
            }
        ]
    """

    with open(load_path, 'r', encoding='utf-8') as file:
        content = file.read()
    try:
        prompt = json.loads(content)
        assert isinstance(prompt, list), "Error: 'prompt' must be a list."
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON in file: {load_path}")
        logger.error(f"Error: {e}")
        logger.warning(f"Automatically transform txt into json")
        prompt = [
            {
                "role": role,
                "content": [
                    {
                        "type": "text",
                        "text": content
                    }
                ]
            }
        ]
        logger.warning(f"The formated json prompt is shown below:\n{prompt}")
    
    return prompt