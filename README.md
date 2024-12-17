**config文件**

**load_path**是多个prompt所在的文件夹名称

**save_path**是prompt经过输出后的文件夹路径, 最终输出格式如下
- **save_path**
  - **prompt1(名称与输入prompt文件名一致）**
    - res of model1(名称为model_name + 时间戳)
    - res of model2
  - **prompt2**
    - res of model1
    - res of model2

**models.name** 必须填写完整的vllm serve时的模型路径（因为vllm会把模型路径设定为网络请求路径），"/"也需要保持一致，假设vllm serve时的路径为/mnt/afs/share/llama-3.2-1B/, models.name也需要是/mnt/afs/share/llama-3.2-1B/（不能省最后的"/")

**models.url** 填写ip地址加端口号,前面加上http://, 如 "http://14.103.16.79:15555"

**models.api_key** 可选项，如果访问的是远端官网api，则输入对应的api_key

<br>

**prompt格式**

一个list，每个元素师一个字典，包含role和content，如下示例

            [
                {"role": "user", "content": "If I say HHH, you answer KKK back to me!"},
                {"role": "assistant", "content": "understood"},
                {"role": "user", "content": "HHH"}
            ]

<br>

**testing流程**

1. 在自己的设备上通过vllm serve "model_name" --port 8000启动模型， 具体启动配置项可参考 https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html#chat-template

2. 按照前文所述配置config.json

3. python start_testing.py

p.s 当前有一个baseline model是deepseek-chat






