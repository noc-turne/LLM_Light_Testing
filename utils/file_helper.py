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


request_body = {
    "temperature": float,           # Sampling temperature, between 0 and 2
    "top_p": float,                 # Nucleus sampling parameter, between 0 and 1
    "n": int,                       # Number of completions to generate, must be a positive integer
    "stream": bool,                 # Whether to stream partial progress, True or False
    "stop": (str, list),            # A string or list of strings to stop generation
    "max_tokens": int,              # The maximum number of tokens to generate, must be a non-negative integer
    "max_completion_tokens": int,   # The maximum number of tokens to generate, must be a non-negative integer
    "presence_penalty": float,      # Penalizes new tokens based on their presence, range: -2.0 to 2.0
    "frequency_penalty": float,     # Penalizes new tokens based on frequency, range: -2.0 to 2.0
    "logit_bias": dict,             # A dictionary mapping tokens (str or int) to bias values (float), range: -100 to 100
    "user": str                     # A unique identifier for your end-user, typically a string
}

def validate_model_config_params(model_config):
    for key, value in model_config.items():
        if key not in request_body:
            return (False, f"Invalid parameter: {key}")

        expected_type = request_body[key]
        if isinstance(expected_type, tuple):
            if not any(isinstance(value, t) for t in expected_type):
                return (False, f"Invalid type for {key}. Expected one of {expected_type}, got {type(value).__name__}.")
        else:
            if not isinstance(value, expected_type):
                return (False, f"Invalid type for {key}. Expected {expected_type.__name__}, got {type(value).__name__}.")

        # Additional validation for specific parameters
        if key == "temperature" and not (0 <= value <= 2):
            return (False, "temperature must be between 0 and 2.")
        if key == "top_p" and not (0 <= value <= 1):
            return (False, "top_p must be between 0 and 1.")
        if key == "n" and value <= 0:
            return (False, "n must be a positive integer.")
        if (key == "max_tokens" or key == "max_completion_tokens") and value < 0:
            return (False, "max_completion_tokens must be a non-negative integer.")
        if key in ["presence_penalty", "frequency_penalty"] and not (-2.0 <= value <= 2.0):
            return (False, f"{key} must be between -2.0 and 2.0.")
        if key == "logit_bias" and not all(
            isinstance(k, (str, int)) and isinstance(v, (int, float)) and -100 <= v <= 100
            for k, v in value.items()
        ):
            return (False, "logit_bias must be a dictionary with keys as tokens (str or int) and values as floats between -100 and 100.")
    
    return (True, "All parameters are valid.")

class ConfigError(Exception):
    """Custom exception for configuration errors."""
    def __init__(self, *args):
        super().__init__(*args)
    
    def __str__(self):
        return "The model_config in config file is not configured correctly. Refer to the documentation for valid configurations: https://platform.openai.com/docs/api-reference/chat/object"




