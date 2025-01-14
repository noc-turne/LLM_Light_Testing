# VLM 测试(BETA版)
本功能用于对视觉大语言模型（如Qwen2-VL-7B）进行测试，当前为Beta版本，支持基于`vLLM`框架的本地部署。

## 目录

- [配置文件说明](#配置文件说明)
- [使用方法](#使用方法)
- [结果保存](#结果保存)

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
    "summary": {
    "model_summary": true,
    "file_summary": true,
    "response_summary": true
    },
    "model_config": {"max_completion_tokens": 100},
    "models": [
        {
            "name": "Qwen2-VL-7B",
            "url": "http://xxx.xxx.xxx.xxx:xxxx",
            "gpu_url": "http://xxx.xxx.xxx.xxx:xxxx",
            "gpu_interval": 3
        }
    ],
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

- 其他配置参数与语言模型保持一致, 详见[配置文件结构](../README.md#%E9%85%8D%E7%BD%AE%E6%96%87%E4%BB%B6%E7%BB%93%E6%9E%84)

## 使用方法

1. **准备数据**：

   根据配置文件中的 `mode` 设置，准备相应的提示文件和图片文件夹。

2. **配置文件**：

   编辑 `config_vlm.json`，根据实际情况填写各项配置。

3. **模型部署**  
   确保模型已部署在本地，通过`vLLM`进行部署。以下是示例命令：
   ```bash
   vllm serve Qwen2-VL-7B --task generate --max-model-len 4096 --allowed-local-media-path path-to-testing_pipeline --limit-mm-per-prompt image=k
   ```

4. **运行脚本**：

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
  - `response_summary_table.csv`：汇总每个测试文件下每个模型的回答内容

具体生成样式可参考[测试结果存储](../README.md#%E6%B5%8B%E8%AF%95%E7%BB%93%E6%9E%9C%E5%AD%98%E5%82%A8)和[表格总结功能](../README.md#%E8%A1%A8%E6%A0%BC%E6%80%BB%E7%BB%93%E5%8A%9F%E8%83%BD)

