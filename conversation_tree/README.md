# 对话生成器

## 项目简介

本项目是一个基于多线程和递归深度优先搜索（DFS）策略的对话生成器。它利用AI模型生成用户和AI之间的对话，通过预设或AI生成的用户提示词，探索不同的话题分支，并将生成的对话树保存到指定路径中。

## 功能特点

- **多线程处理**：在对话树的第一层使用多线程加速处理，提升生成效率。
- **灵活的用户提示生成**：支持预设提示、AI生成提示或用户手动输入提示。
- **递归DFS策略**：通过深度优先搜索策略，系统性地扩展对话树。
- **配置文件支持**：通过JSON配置文件灵活配置对话生成参数。
- **日志记录**：详细的日志记录，便于调试和监控。

## 配置文件说明

项目使用一个JSON格式的配置文件 `conversation_config.json` 来配置对话生成的参数。以下是配置项的详细说明：

```json
{
    "background_name": "询问",
    "background_conversation_file": "example_files/background_conversation.txt",
    "topic_chosen_file": "example_files/topic_chosen.txt",
    "save_path": "res",
    "user_prompt_generator_type": "AI",
    "preset_user_prompt_file": ""
}
```

### 配置项解释

- **background_name** (`string`): 对话生成的背景名称，用于文件命名。
  
- **background_conversation_file** (`string`): 包含背景对话的文本文件路径。该文件应包含初始对话内容，以JSON格式存储。
  
- **topic_chosen_file** (`string`): 包含可选话题的文本文件路径。该文件应是一个JSON格式的列表，列出所有可供选择的话题。
  
- **save_path** (`string`): 生成的对话文件保存的目录路径。程序会在此路径下创建文件夹并保存对话记录。
  
- **user_prompt_generator_type** (`string`): 用户提示词的生成方式。可选值包括：
  - `"AI"`: 由AI模型生成用户提示词。
  - `"preset"`: 使用预设的用户提示词。
  - `"user"`: 由用户手动输入提示词。
  
- **preset_user_prompt_file** (`string`): 当 `user_prompt_generator_type` 设置为 `"preset"` 时，指定预设用户提示词的JSON文件路径。该文件应是一个字典，键为话题，值为对应的用户提示词, 需保证键值的列表与topci_chosen_file一致。

## 使用说明

### 准备工作

1. **配置背景对话文件**：编辑 `example_files/background_conversation.txt`，确保其包含初始对话内容，并以JSON格式保存。

2. **配置话题列表**：编辑 `example_files/topic_chosen.txt`，列出所有可供选择的话题，并以JSON格式保存为列表。

3.**配置其他config文件参数**

4. **（可选）配置预设用户提示词**：如果选择使用预设提示词，编辑相应的JSON文件，确保其格式为字典，且键与 `topic_chosen_file` 中的内容一致。

### 运行程序

在命令行中运行以下命令启动对话生成器：

```bash
python conversation_generator.py
```

程序将根据配置文件中的参数生成对话树，并将结果保存到指定的 `save_path` 目录中。

### 生成结果

生成的对话记录将以JSON格式保存在 `save_path` 指定的目录中，文件名包含背景名称、话题、扩展轮数和时间戳。例如：

```
res/询问_话题1_话题2_6_20250110_123456.txt
```


## 注意事项

- **API密钥**：确保在调用AI模型时使用有效的API密钥。代码中示例使用了占位符 `"token-123"`，请根据实际情况替换。

- **模型URL和名称**：根据实际使用的AI模型，调整 `model_url` 和 `model_name` 参数。

