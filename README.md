# README

## 目录
- [目的](#%E7%9B%AE%E7%9A%84)
- [功能](#%E5%8A%9F%E8%83%BD)
- [安装](#%E5%AE%89%E8%A3%85)
- [使用指南](#%E4%BD%BF%E7%94%A8%E6%8C%87%E5%8D%97)
- [常见问题](#%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98)

---

## 目的
本项目旨在提供一个自动化测试框架，用于对多个模型进行验证与对比，特别是基于[vLLM](https://docs.vllm.ai)框架部署的模型。通过本工具，用户可以快速评估不同模型在相同输入下的性能，并将结果归档，便于后续分析与调试。

---

## 功能
1. **多模型测试**：支持同时测试多个模型，便于性能对比。
2. **灵活配置**：通过`config.json`文件灵活配置模型路径、URL、API密钥等参数。
3. **统一输出格式**：测试结果按模型和输入分类存储，支持后续自动化分析。
4. **多轮对话支持**：支持复杂的多轮对话输入，便于验证模型交互能力。
5. **表格总结功能**：自动生成表格汇总测试结果，便于性能对比和分析。

---

## 使用指南

### 配置文件结构

`config.json`配置文件包含以下主要字段：

- **`model_count`**: 需要测试的模型数量，必须与`models`列表长度一致。
- **`load_path`**: Prompt文件的输入路径。
- **`save_path`**: 测试结果的输出路径。
- **`models`**: 模型列表，每个模型包含：
  - **`name`**: 模型路径，与`vLLM`服务路径一致。
  - **`url`**: 模型的IP地址与端口，并在开头加上"http://"。
  - **`api_key`**: （可选）远端API的密钥。

示例：

```json
{
    "model_count": 2,
    "load_path": "./prompts",
    "save_path": "./results",
    "models": [
        {
            "name": "/mnt/afs/share/llama-3.2-1B/",
            "url": "http://127.0.0.1:8000",
        },
        {
            "name": "deepseek-chat", 
            "url": "https://api.deepseek.com", 
            "api_key": "sk-123456"
        }
    ]
}
```

### Prompt文件格式
Prompt文件为一个JSON列表，每个元素包含以下字段：
- **`role`**: 交互角色（如`user`或`assistant`）。
- **`content`**: 交互内容。

示例：
```json
[
    {"role": "user", "content": "If I say HHH, you answer KKK back to me!"},
    {"role": "assistant", "content": "understood"},
    {"role": "user", "content": "HHH"}
]
```

### 运行测试

1. 配置`config.json`文件。
2. 运行测试脚本。
   ```bash
   python start_testing.py
   ```
3. 测试结果按以下结构存储：
   ```
   save_path/
   ├── prompt1/
   │   ├── res_of_model1.json
   │   └── res_of_model2.json
   ├── prompt2/
   │   ├── res_of_model1.json
   │   └── res_of_model2.json
   ```

### 表格总结功能

程序会生成一个总结表格，用于对测试结果进行汇总分析。表格结构示例如下：

| Prompt        | Model                                    | Prompt Token Length | Decode Token Length | Elapsed Time(s) | Decode Speed(Token/s) |
|---------------|------------------------------------------|---------------------|----------------------|-----------------|------------------------|
| prompt1.txt   | /mnt/afs/share/llama-3.2-1B-instruct     | -1                  | -1                   | -1              | -1                     |
|               | deepseek-chat                            | 23                  | 2                    | 0.85            | 2.35                   |
| prompt2.txt   | /mnt/afs/share/llama-3.2-1B-instruct     | -1                  | -1                   | -1              | -1                     |
|               | deepseek-chat                            | 23                  | 2                    | 0.94            | 2.13                   |

总结表格存储在`save_path`目录下，文件格式为`.xlsx`，方便使用Excel或其他工具查看。

---

## 常见问题

### 1. 如何解决`vLLM`服务无法启动？
- 确保模型路径正确，且目录中包含必要的模型文件。
- 确认`vLLM`安装完整，依赖已安装。

### 2. 为什么测试脚本运行报错？
- 检查`config.json`文件是否正确配置。
- 确认Prompt文件格式是否符合要求。

### 3. 如何增加更多模型？
- 在`config.json`中增加新的模型配置，并确保其`name`和`url`与实际部署一致。

### 4. 输出结果中的时间单位是什么？
- 所有时间（如`elapsed_time`）均以秒为单位，方便性能分析。

### 5. 表格中的`-1`值代表什么？
- `-1`表示对应字段无效，例如模型未成功解码Token或响应时间超时。

---

如果有更多问题，请提交到[Issues](https://github.com/your-repository-url/issues)页面。