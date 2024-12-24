from flask import Flask, jsonify
import pynvml

app = Flask(__name__)

def get_gpu_info():
    pynvml.nvmlInit()
    device_count = pynvml.nvmlDeviceGetCount()
    gpu_info = []
    for i in range(device_count):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        name = pynvml.nvmlDeviceGetName(handle)
        # 在较新版本的 pynvml 中，直接使用 name（无需 decode）
        if isinstance(name, bytes):
            name = name.decode('utf-8')
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        gpu_info.append({
            "gpu_id": i,
            "name": name,
            "gpu_utilization": utilization.gpu,
            "memory_utilization": utilization.memory,
            "memory_used": memory_info.used // 1024**2,
            "memory_total": memory_info.total // 1024**2
        })
    pynvml.nvmlShutdown()
    return gpu_info

@app.route('/gpu_info', methods=['GET'])
def gpu():
    return jsonify(get_gpu_info())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
