import redis
import time
import csv
import os
from datetime import datetime, timedelta
import asyncio
from instructor.utils import get_config, make_redis_client


cfg = get_config()
redis_client = make_redis_client()

detection_keys = []
for point in cfg["pose_keypoints"]:
    detection_keys.append(cfg["redis"]["realsense_prefix"] + point)

prev = {key: [] for key in detection_keys}
history = {key: [] for key in detection_keys}

recordings_dir = cfg["dirs"]["recordings"]
os.makedirs(recordings_dir, exist_ok=True)
history_file = os.path.join(recordings_dir, "history.txt")

def initialize_output_file():
    with open(history_file, 'w') as file:
        header = ['timestamp'] + detection_keys
        file.write('\t'.join(header) + '\n')

def append_to_output_file(history):
    """
    Append rows of data from the history to the output file.
    Each row includes a timestamp followed by the values for each key.
    """
    with open(history_file, 'a') as file:
        for timestamp in sorted(set(entry['timestamp'] for key in history for entry in history[key])):
            row = [timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')] + [next((entry['value'] for entry in history[key] if entry['timestamp'] == timestamp), 'None') for key in detection_keys]
            file.write('\t'.join(row) + '\n')

def read_and_append_keys():
    """
    Continuously read from the specified Redis keys and append their values to the output file.
    Publish each key at a rate of 30 Hz.
    """
    initialize_output_file()
    key_index = 0
    while True:
        current_time = datetime.now()
        for key_index in range(len(detection_keys)):
            key = detection_keys[key_index]

            try:
                value = redis_client.get(key)
                if value is not None:
                    if key not in history:
                        history[key] = []
                    history[key] = [{'timestamp': current_time, 'value': value}]
            except redis.ConnectionError as e:
                print(f"Redis connection error: {e}")
                return
            
        key_changed = [not prev[key] or prev[key][0]["value"] != history[key][0]["value"] for key in detection_keys]
        if any(key_changed):
            append_to_output_file(history)

        for key in prev: 
            prev[key] = history[key].copy()
        time.sleep(1.0 / 20)  # Maintain a rate of 30 Hz per key

def test():
    print("History saving function is running.")

if __name__ == "__main__":
    test()
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, read_and_append_keys)
    loop.run_forever()