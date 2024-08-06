import redis
import time
import csv
from datetime import datetime, timedelta
import asyncio

HISTORY_FILE = 'recordings/history.txt'  # Output file for the data

# Redis configuration
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

RIGID_BODY_POSITION_KEYS = [
    "sai2::realsense::left_hand",
    "sai2::realsense::right_hand",
    "sai2::realsense::center_hips"
]

history = {key: [] for key in RIGID_BODY_POSITION_KEYS}

def cleanup_old_entries(history, current_time):
    """
    Remove entries older than 30 seconds from the history.
    """
    cutoff_time = current_time - timedelta(seconds=30)
    for key in list(history.keys()):
        history[key] = [entry for entry in history[key] if entry['timestamp'] >= cutoff_time]
        if not history[key]:
            del history[key]

def initialize_output_file():
    """
    Initialize the output file with a header row containing the keys.
    """
    with open(HISTORY_FILE, 'w') as file:
        header = ['timestamp'] + RIGID_BODY_POSITION_KEYS
        file.write('\t'.join(header) + '\n')

def append_to_output_file(history):
    """
    Append rows of data from the history to the output file.
    Each row includes a timestamp followed by the values for each key.
    """
    with open(HISTORY_FILE, 'a') as file:
        for timestamp in sorted(set(entry['timestamp'] for key in history for entry in history[key])):
            row = [timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')] + [next((entry['value'] for entry in history[key] if entry['timestamp'] == timestamp), 'None') for key in RIGID_BODY_POSITION_KEYS]
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
        key = RIGID_BODY_POSITION_KEYS[key_index]

        try:
            value = redis_client.get(key)
            if value is not None:
                if key not in history:
                    history[key] = []
                history[key].append({'timestamp': current_time, 'value': value})
        except redis.ConnectionError as e:
            print(f"Redis connection error: {e}")
            return

        cleanup_old_entries(history, current_time)
        append_to_output_file(history)

        key_index = (key_index + 1) % len(RIGID_BODY_POSITION_KEYS)
        time.sleep(1.0 / 30)  # Maintain a rate of 30 Hz per key

def test():
    print("History saving function is running.")

if __name__ == "__main__":
    test()
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, read_and_append_keys)
    loop.run_forever()