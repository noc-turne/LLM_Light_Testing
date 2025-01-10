import logging
import os
import asyncio
from datetime import datetime
import aiohttp


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
current_file = os.path.splitext(os.path.basename(__file__))[0]
logger = logging.getLogger(current_file)


# GPU RELATED
def gpu_info2txt(file_name, response):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(file_name, "a") as file:
        file.write(f"Current Time: {timestamp}\n")
        for gpu in response:
            file.write(f"GPU {gpu['gpu_id']} ({gpu['name']}):\n")
            file.write(f"  GPU Utilization: {gpu['gpu_utilization']}%\n")
            file.write(f"  Memory Utilization: {gpu['memory_utilization']}%\n")
            file.write(f"  Memory: {gpu['memory_used']} MiB / {gpu['memory_total']} MiB\n")
            file.write("\n")
        file.write("\n")


async def fetch_gpu_info(api_url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Received status code {response.status} for URL {api_url}")
                    return None
        except Exception as e:
            logger.error(f"Failed to fetch GPU info from {api_url}. Exception: {e}")
            return None


async def monitor_gpu(api_url, interval, file_name, stop_event):
    while not stop_event.is_set():
        response = await fetch_gpu_info(api_url)
        if response:  # Ensure the response is valid
            gpu_info2txt(file_name, response)
        await asyncio.sleep(interval)


async def gpu_main(models, save_path, stop_event):
    tasks = []
    gpu_info_path = os.path.join(save_path, "gpu_info")
    os.makedirs(gpu_info_path, exist_ok=True)
    for idx, model in enumerate(models):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{idx}"
        if "gpu_url" not in model.keys():
            continue
        normalized_path = model['name'].rstrip("/")
        file_name = os.path.join(gpu_info_path, os.path.basename(normalized_path) + f"_{timestamp}.txt")
        if "gpu_interval" not in model.keys():
            interval = 3
        else:
            interval = model['gpu_interval']
        tasks.append(
            monitor_gpu(
                model['gpu_url'] + "/gpu_info",
                interval=interval,
                file_name=file_name,
                stop_event=stop_event
            )
        )

    await asyncio.gather(*tasks)