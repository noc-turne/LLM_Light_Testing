# README

## 目录
- [目的](#%E7%9B%AE%E7%9A%84)
- [功能](#%E5%8A%9F%E8%83%BD)
- [安装](#%E5%AE%89%E8%A3%85)
- [使用指南](#%E4%BD%BF%E7%94%A8%E6%8C%87%E5%8D%97)
  - [配置文件结构](#%E9%85%8D%E7%BD%AE%E6%96%87%E4%BB%B6%E7%BB%93%E6%9E%84)
  - [Prompt文件格式](#prompt%E6%96%87%E4%BB%B6%E6%A0%BC%E5%BC%8F)
  - [运行测试流程](#%E8%BF%90%E8%A1%8C%E6%B5%8B%E8%AF%95%E6%B5%81%E7%A8%8B)
  - [测试结果存储](#%E6%B5%8B%E8%AF%95%E7%BB%93%E6%9E%9C%E5%AD%98%E5%82%A8)
  - [表格总结功能](#%E8%A1%A8%E6%A0%BC%E6%80%BB%E7%BB%93%E5%8A%9F%E8%83%BD)
  - [GPU监控支持](#gpu%E7%9B%91%E6%8E%A7%E6%94%AF%E6%8C%81)
  - [视觉大语言模型测试（BETA版）](#%E8%A7%86%E8%A7%89%E5%A4%A7%E8%AF%AD%E8%A8%80%E6%A8%A1%E5%9E%8B%E6%B5%8B%E8%AF%95beta%E7%89%88)
- [常见问题](#%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98)

---

## 目的
本项目旨在提供一个大语言模型自动化测试框架，特别是基于[vLLM](https://docs.vllm.ai)框架部署的模型。用户可通过配置文件, 一键式实现对多prompt文件及多模型的测试。框架会将生成结果自动归档，并对测试结果生成多个总结表格。同时，框架也支持视觉大语言模型的自动化测试以及服务器模型处理时的gpu指标监测。

---

## 功能
1. **多prompt文件多模型测试**：支持同时测试多个prompt文件和多个模型，便于性能对比。
2. **灵活配置**：通过`config.json`文件灵活配置模型路径、URL、API密钥等参数。
3. **统一输出格式**：测试结果按模型和输入分类存储，支持后续自动化分析。
4. **表格总结功能**：自动生成表格汇总测试结果，便于性能对比和分析。
5. **GPU监控支持**：提供对模型运行时GPU使用情况的监控和记录。
6. **视觉大语言模型支持（BETA）**： 提供本地部署视觉大语言模型的自动化测试

---

## 安装

### 服务器端安装
1. 克隆项目到本地服务器：
   ```bash
   git clone https://github.com/noc-turne/testing_pipeline.git
   cd testing_pipeline
   ```

2. 安装所需依赖
   ```bash
   pip install -r requirements-server.txt
   ```

3. 验证是否安装成功
   ```bash
   vllm serve 本地模型路径
   ```

### 客户端安装
1. 克隆项目到本地服务器：
   ```bash
   git clone https://github.com/noc-turne/testing_pipeline.git
   cd testing_pipeline
   ```

2. 安装所需依赖
   ```bash
   pip install -r requirements-client.txt
   ```

## 使用指南

### 配置文件结构

`config.json`配置文件包含以下主要字段：

- **`load_path`**: Prompt文件的输入路径。
- **`save_path`**: 测试结果的输出路径。
- **`save_response`**: bool值(可选, 默认为true)，是否需要输出每个prompt的模型运行结果的json文件
- **`summary`**: 字典类型(可选, 默认均为true), 其中包含三个键model_summary，file_summary和response_summary, 其值为bool, 用于是否输出的对应的summary文件，对应的summary文件示例可查看[表格总结功能](#%E8%A1%A8%E6%A0%BC%E6%80%BB%E7%BB%93%E5%8A%9F%E8%83%BD)
- **`model_config`**: 字典类型(可选, 默认为空), 发送请求时的具体配置, 包括max_completion_tokens, temperature, top-p等, 应用于所有模型, 具体配置内容可参考(https://platform.openai.com/docs/api-reference/chat/object)
- **`models`**: 模型列表，每个模型包含：
  - **`name`**: 模型路径，与`vLLM`服务路径一致, 不可以重名。
  - **`url`**: 模型的IP地址与端口，并在开头加上"http://"。
  - **`api_key`**: （可选）远端API的密钥。
  - **`gpu_url`**: （可选）GPU监控的API地址，用于获取GPU使用信息。
  - **`gpu_interval`**: int类型（可选, 默认为3）, GPU信息采样间隔时间，单位为秒。

示例：

```json
{
    "load_path": "examples/prompts", 
    "save_path": "examples/res",
    "save_response": true,
    "summary": {
    "model_summary": true,
    "file_summary": true,
    "response_summary": true
    },
    "model_config": {"max_completion_tokens": 100},
    "models": [
      {
        "name": "llama-3.3-70B-instruct",
        "url": "http://xxx.xxx.xxx.xxx:xxxx",
        "gpu_url": "http://xxx.xxx.xxx.xxx:xxxx",
        "gpu_interval": 3
      },
      {
        "name": "deepseek-chat",
        "url": "https://api.deepseek.com",
        "api_key": "sk-token123"
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

### 运行测试流程

1. 服务端通过vllm部署模型网络接口，具体部署参数可详见(https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)。
   ```bash
   vllm serve 本地模型路径
   ```

2. 服务端启动GPU监控脚本（如果需要），具体可见[GPU监控支持](#gpu%E7%9B%91%E6%8E%A7%E6%94%AF%E6%8C%81)：
   ```bash
   python gpu_monitor.py
   ```

3. 将需要测试的prompts整理成一个文件夹如`examples/prompts`。
4. 客户端配置`config.json`文件。
5. 客户端运行测试脚本。
   ```bash
   python start_testing.py
   ```

### 测试结果存储
测试结果按以下结构存储：
```
save_path/
├── prompt1/
│   ├── res_of_model1.json
│   └── res_of_model2.json
├── prompt2/
│   ├── res_of_model1.json
│   └── res_of_model2.json
├── gpu_info/
│   ├── res_of_model1.txt
│   └── res_of_model2.txt
├── file_summary_table.xlsx
├── model_summary_table.xlsx
├── response_summary_table.xlsx

```

每个prompt的具体输出如下所示, 可通过配置文件中的save_response选择是否输出：
```json
{
   "file": "prompt1.txt",
   "model": "llama-3.3-70B-instruct",
   "model_url": "http://xxx.xxx.xxx.xxx:xxxx",
   "start_time": "2024-12-27T16:09:53.610822",
   "prompt": [
      {
            "role": "user",
            "content": "If I say HHH, you answer KKK back to me!"
      },
      {
            "role": "assistant",
            "content": "understood"
      },
      {
            "role": "user",
            "content": "HHH"
      }
   ],
   "end_time": "2024-12-27T16:09:54.072932",
   "elapsed_time": 0.46211,
   "prompt_token_len": 63,
   "decode_token_len": 3,
   "response": {
      "role": "assistant",
      "content": "KKK",
      "tool_calls": []
   }
}
   ```

### 表格总结功能

程序会生成多个表格，用于对测试结果进行汇总分析。

文件总结表格（file_summary_table.xlsx）结构示例如下：

| Prompt        | Model                                    | Prompt Token Length | Decode Token Length | Elapsed Time(s) | Decode Speed(Token/s) |
|---------------|------------------------------------------|---------------------|----------------------|-----------------|------------------------|
| prompt1.txt   | llama-3.3-70B-instruct                   | -1                  | -1                   | -1              | -1                     |
|               | deepseek-chat                            | 23                  | 2                    | 0.85            | 2.35                   |
| prompt2.txt   | llama-3.3-70B-instruct                   | -1                  | -1                   | -1              | -1                     |
|               | deepseek-chat                            | 23                  | 2                    | 0.94            | 2.13                   |

模型总结表格（model_summary_table.xlsx）结构示例如下：
| Model                                    | Total Prompt Tokens | Total Decode Tokens  | Total Runtime(s) | Decode Speed(Token/s) |
|------------------------------------------|---------------------|----------------------|-----------------|------------------------|
| llama-3.3-70B-instruct                   | -1                  | -1                   | -1              | -1                     |
| deepseek-chat                            | 115255              | 18673                | 29.38           | 635.56                 |

回答表格（response_summary_table.xlsx） 结构示例如下：
| Prompt        | Model                                    |Response
|---------------|------------------------------------------|----------------
| prompt1.txt   | llama-3.3-70B-instruct                   | KKK
|               | deepseek-chat                            | KKK
| prompt2.txt   | llama-3.3-70B-instruct                   | ### The Future of Artificial Intelligence in Education ...
|               | deepseek-chat                            | # The Future of Artificial Intelligence in Education ...

总结表格存储在`save_path`目录下，文件格式为`.xlsx`，方便使用Excel或其他工具查看。

### GPU监控支持

本工具支持在测试过程中对模型运行的GPU使用情况进行实时监控，记录每个模型的GPU负载和显存使用情况，方便用户分析模型性能表现。

#### 流程
1. 在服务端运行gpu_monitor.py, 开放网络接口，使得当前测试端可以获取到服务端的gpu信息
```bash
python gpu_monitor.py
```
2. 在`config.json`文件中配置每个模型的`gpu_url`和`gpu_interval`。
   - `gpu_url`：获取GPU使用信息的API地址。
   - `gpu_interval`：采样间隔时间（秒）。
3. 测试脚本启动后，工具会根据配置定期从`gpu_url`拉取GPU使用信息。
4. GPU信息按模型存储在`save_path/gpu_info`目录下，文件名为`<模型名称>_<时间戳>.txt`。

#### 输出示例
以下是GPU监控记录的输出示例：

```
Current Time: 20241224_120000
GPU 0 (NVIDIA A100):
  GPU Utilization: 75%
  Memory Utilization: 60%
  Memory: 24300 MiB / 40000 MiB

GPU 1 (NVIDIA A100):
  GPU Utilization: 65%
  Memory Utilization: 55%
  Memory: 22000 MiB / 40000 MiB

Current Time: 20241224_121000
GPU 0 (NVIDIA A100):
  GPU Utilization: 80%
  Memory Utilization: 60%
  Memory: 24300 MiB / 40000 MiB

GPU 1 (NVIDIA A100):
  GPU Utilization: 75%
  Memory Utilization: 55%
  Memory: 22000 MiB / 40000 MiB
```

每次采样的时间戳和每张GPU的利用率、显存利用率、以及显存使用情况均会记录，便于后续分析。

---

### 视觉大语言模型测试（BETA版）

具体信息可见(https://github.com/noc-turne/testing_pipeline/tree/main/vlm)

本功能用于对视觉大语言模型（如Qwen2-VL-7B）进行测试，当前为测试版本，支持基于`vLLM`框架的本地部署。

#### 测试流程

1. **模型部署**  
   确保模型已部署在本地，通过`vLLM`进行部署。以下是示例命令：
   ```bash
   vllm serve Qwen2-VL-7B --task generate --max-model-len 4096 --allowed-local-media-path path-to-testing_pipeline --limit-mm-per-prompt image=k
   ```

2. **配置`config_vlm.json`**  
   创建并配置`config_vlm.json`文件，其内容暂时与`config.json`一致。

3. **准备测试文件**  
   测试文件结构示例：
   ```
   load_path/
   ├── test1/
   │   ├── prompt1.txt
   │   ├── images/
   │   │   ├── a.jpg
   │   │   └── b.jpg
   ├── test2/
   │   ├── prompt2.txt
   │   ├── images/
   │   │   ├── c.jpg
   │   │   └── d.jpg
   ```

4. **运行测试脚本**  
   运行以下命令启动测试：
   ```bash
   python start_testing_vlm.py
   ```

#### 注意事项
- 测试文件目录中，`prompt1.txt`存储测试的文本提示，`images`目录下存储相关联的图像文件。
- 确保`allowed-local-media-path`指向testing_pipeline的本机目录。
- 当前仅支持单机本地部署测试。


## 常见问题

### 1. 如何解决`vLLM`服务无法启动？
- 确保模型路径正确，且目录中包含必要的模型文件。
- 确保config文件中模型name与vllm serve中的模型名称一致

### 2. 为什么测试脚本运行报错？
- 检查`config.json`文件是否正确配置。
- 确认Prompt文件格式是否符合要求。
- 根据报错信息检查服务器模型端口是否可以被访问

### 3. 如何增加更多模型？
- 在`config.json`中增加新的模型配置，并确保其`name`和`url`与实际部署一致。

### 4. 输出结果中的时间单位是什么？
- 所有时间（如`elapsed_time`）均以秒为单位，方便性能分析。

### 5. 表格中的`-1`值代表什么？
- `-1`表示对应字段无效，例如模型未成功解码Token或响应时间超时。

---

如果有更多问题，请提交到[Issues](https://github.com/noc-turne/testing_pipeline/issues)页面。

