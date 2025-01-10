# VLM 测试(BETA版)

本项目是一个用于处理视觉语言模型（VLM）测试的管道。它支持多模型并行处理，通过异步请求与模型进行交互，记录响应时间和令牌使用情况，并监控 GPU 资源使用。最终，测试结果将以多种格式保存，便于后续分析和评估。

## 目录

- [功能介绍](#功能介绍)
- [配置文件说明](#配置文件说明)
- [使用方法](#使用方法)
- [结果保存](#结果保存)
- [常见问题与调试](#常见问题与调试)

## 功能介绍

- **多模型并行处理**：支持同时向多个模型发送请求，提高测试效率。
- **异步请求**：利用 `asyncio` 和 `httpx` 实现异步 HTTP 请求，优化响应时间。
- **GPU 监控**：实时监控 GPU 使用情况，确保资源的合理利用。
- **结果记录与保存**：记录每次请求的详细信息，包括响应时间、令牌使用情况等，并支持将响应内容保存为 JSON 和 CSV 格式。
- **灵活配置**：通过配置文件自定义测试模式、路径、模型信息等。

## 配置文件说明

项目使用 JSON 格式的配置文件 `config_vlm.json` 来定义测试参数。以下是配置文件的示例及说明：

```json
{
    "load_config": {
        "mode": 0,
        "load_path": "vlm_examples/mode0"
    },
    "save_path": "vlm_res",
    "save_response": true,
    "models": [
        {
            "name": "Qwen2-VL-7B",
            "url": "http://14.103.16.79:11004",
            "gpu_url": "http://14.103.16.79:11005",
            "gpu_interval": 3
        }
    ],
    "model_config": {}
}
```

```json
{
    "load_config": {
        "mode": 1,
        "load_images_path": "vlm_examples/mode1/images",
        "load_prompt_path": "vlm_examples/mode1/prompt.txt"
    },
    ...
}
```

### 配置项说明

- `load_config`：定义加载数据的配置。
  - `mode`：
    - `0`：一般性的情况，针对不同prompt对应不同images的一般性场景, 加载路径下测试文件结构如下所示：
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
    - `1`：prompt保持不变，每次输入的图片变化，且每次输入一个图片。
      - `load_images_path`：图片文件夹加载路径。
      - `load_prompt_path`：prompt文件加载路径。
      加载路径下测试文件结构如下所示：
    ```
    load_images_path/
    ├── a.jpg
    ├── b.jpg

- `save_path`：结果保存路径。

- `save_response`：是否保存模型响应内容。`true` 表示保存，`false` 表示不保存。

- `models`：定义要测试的模型列表。
  - `name`：模型名称。
  - `url`：模型 API 端点 URL。
  - `gpu_url`（可选）：GPU 监控的 API URL。
  - `gpu_interval`（可选）：GPU 监控的时间间隔（秒）。

- `model_config`（可选）：模型的其他配置参数，可根据需要添加。

## 使用方法

1. **准备数据**：

   根据配置文件中的 `mode` 设置，准备相应的提示文件和图片文件夹。

2. **配置文件**：

   编辑 `config_vlm.json`，根据实际情况填写各项配置。

3. **运行脚本**：

   在终端中运行以下命令：

   ```bash
   python start_testing_pipeline_vlm.py
   ```

## 结果保存

测试完成后，结果将保存在 `save_path` 指定的目录中，包括：

- **响应内容**：如果 `save_response` 设置为 `true`，每个模型的响应将保存为 JSON 文件，文件名包含模型名称和时间戳。
- **汇总表格**：
  - `file_summary_table.csv`：汇总每个测试文件的结果。
  - `model_summary_table.csv`：汇总每个模型的整体表现。
  - `response_table_<model>.csv`：按模型分类的响应内容, 保存在 `save_path`对应模型的文件夹下


## 常见问题与调试

### 1. 模式配置错误

**问题**：配置文件中 `mode` 设置不正确，导致数据加载失败。

**解决方法**：确保 `mode` 设置为 `0` 或 `1`，并根据模式正确配置 `load_path`、`load_images_path` 和 `load_prompt_path`。

### 2. 结果文件未生成

**问题**：结果未保存到指定路径。

**解决方法**：

- 确认 `save_path` 配置正确，并且脚本具有写入权限。
- 检查 `save_response` 是否设置为 `true`，以及保存过程是否有异常。
