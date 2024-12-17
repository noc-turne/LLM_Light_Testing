**config文件**

**model_count**： 需要测试的模型个数，与下文的models列表长度需保持一致

**load_path**是多个prompt所在的文件夹名称

**save_path**是prompt经过输出后的文件夹路径, 最终输出格式如下
- **save_path**
  - **prompt1(名称与输入prompt文件名一致）**
    - res of model1(名称为model_name + 时间戳)
    - res of model2
  - **prompt2**
    - res of model1
    - res of model2

**models**是一个列表，其中可包含多个model

**model.name** 必须填写完整的vllm serve时的模型路径（因为vllm会把模型路径设定为网络请求路径），"/"也需要保持一致，假设vllm serve时的路径为/mnt/afs/share/llama-3.2-1B/, models.name也需要是/mnt/afs/share/llama-3.2-1B/（不能省最后的"/")

**model.url** 填写ip地址加端口号,前面加上http://, 如 "http://14.103.16.79:15555"

**model.api_key** 可选项，如果访问的是远端官网api，则输入对应的api_key


<br>

**prompt格式**

一个list，每个元素是一个字典，包含role和content，如下示例

            [
                {"role": "user", "content": "If I say HHH, you answer KKK back to me!"},
                {"role": "assistant", "content": "understood"},
                {"role": "user", "content": "HHH"}
            ]

<br>

**输出格式**
```
{
    "file": "prompt1.txt",
    "model": "deepseek-chat",
    "model_url": "https://api.deepseek.com",
    "start_time": "2024-12-17T17:31:38.282322",
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
    "elapsed_time": 0.6917836666107178,
    "prompt_token_len": 23,
    "decode_token_len": 2,
    "response": {
        "role": "assistant",
        "content": "KKK"
    }
}
```

<br>

**testing流程**

1. 在自己的设备上通过vllm serve "model_name" --port 8000启动模型， 具体启动配置项可参考 https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html#chat-template

2. 按照前文所述配置config.json

3. python start_testing.py







