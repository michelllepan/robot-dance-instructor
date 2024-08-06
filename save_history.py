import redis
import time
import csv
from datetime import datetime, timedelta
import asyncio
from run_interpolation import interpolate

HISTORY_FILE = '/Users/rheamalhotra/Desktop/robotics/react-genie-robotics/optitrack/recordings/history.txt'  # Output file for the data

# Redis configuration
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

DEFINE_MOVE_KEY = "robot::define_move"
MOVE_LIST_KEY = "robot::move_list"
EXECUTE_FLAG_KEY = "robot::execute_flag"
MOVE_EXECUTED_KEY = "robot::move_executed"

RIGID_BODY_POSITION_KEYS = [
    "sai2::realsense::left_hand",
    "sai2::realsense::right_hand",
    "sai2::realsense::center_hips"
]
        
PANDA_RIGHT_HAND_POS = "mmp_panda::right_hand"
PANDA_LEFT_HAND_POS = "mmp_panda::realsense::left_hand"
PANDA_CENTER_HIPS_POS = "mmp_panda::realsense::center_hips"

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
    """
    initialize_output_file()
    while True:
        current_time = datetime.now()
        data = {}
        for key in RIGID_BODY_POSITION_KEYS:
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
        time.sleep(1.0 / 120)  # Maintain a rate of 120 Hz

async def get_move_data():
    move_data = await redis_client.lrange(DEFINE_MOVE_KEY, 0, -1)
    moves = []
    for move in move_data:
        parts = move.split(':')
        move_id = parts[0]
        start_time = float(parts[1])
        stop_time = float(parts[2])
        moves.append({
            'move_id': move_id,
            'start_time': start_time,
            'stop_time': stop_time
        })
    return moves

def extract_coordinates_for_move(start_time, stop_time):
    coordinates = []
    with open(HISTORY_FILE, 'r') as file:
        reader = csv.DictReader(file, delimiter='\t')
        for row in reader:
            timestamp = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
            if start_time <= timestamp <= stop_time:
                coordinates.append(row)
    return coordinates

def save_move_coordinates(move_id, coordinates):
    output_file = f"recordings/{move_id}.txt"
    with open(output_file, 'w') as file:
        writer = csv.DictWriter(file, fieldnames=coordinates[0].keys(), delimiter='\t')
        writer.writeheader()
        writer.writerows(coordinates)

async def process_moves():
    moves = await get_move_data()
    for move in moves:
        start_time = datetime.fromtimestamp(move['start_time'])
        stop_time = datetime.fromtimestamp(move['stop_time'])
        coordinates = extract_coordinates_for_move(start_time, stop_time)
        if coordinates:
            save_move_coordinates(move['move_id'], coordinates)
            interpolate
            await redis_client.rpush(MOVE_LIST_KEY, move['move_id'])
            # Remove the processed move from the Redis list
            await redis_client.lrem(DEFINE_MOVE_KEY, 0, f"{move['move_id']}:{move['start_time']}:{move['stop_time']}")
            
            move_id = move['move_id']
            output_file = f"recordings/{move_id}.txt"
            interpolate(output_file, 0.2)

async def replay_moves():
    while True:
        execute_flag = await redis_client.get(EXECUTE_FLAG_KEY)
        if execute_flag == "1":
            move_id = await redis_client.lpop(MOVE_LIST_KEY)
            if move_id:
                await execute_move(move_id)
                await redis_client.rpush(MOVE_EXECUTED_KEY, move_id)
            else:
                await redis_client.set(EXECUTE_FLAG_KEY, "0")
        await asyncio.sleep(0.1)

async def execute_move(move_id):
    file_path = f"/Users/rheamalhotra/Desktop/robotics/react-genie-robotics/optitrack/recordings/{move_id}.txt"
    data = read_data(file_path)
    if data:
        await publish_to_redis(data, rate_hz=30)

def read_data(file_path):
    """
    Read data from the input file and return it as a list of dictionaries.
    Each dictionary represents a row with key-value pairs.
    """
    data = []
    try:
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file, delimiter='\t')
            for row in reader:
                data.append(row)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
    return data

async def publish_to_redis(data, rate_hz):
    """
    Publish each row of data to Redis, for panda to execute.
    """
    interval = 1.0 / rate_hz
    for row in data:
        timestamp = row.pop('timestamp', None)
        for key, value in row.items():
            new_key = "mmp_panda::" + key.split("::")[2]
            await redis_client.set(new_key, value)
        await asyncio.sleep(interval)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(read_and_append_keys())
    loop.create_task(process_moves())
    loop.create_task(replay_moves())
    loop.run_forever()
