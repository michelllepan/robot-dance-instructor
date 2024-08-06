import redis
import time
import csv
from datetime import datetime, timedelta
import asyncio
from run_interpolation import interpolate

HISTORY_FILE = 'recordings/history.txt'  # Output file for the data

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

def get_move_data():
    move_data = redis_client.get(DEFINE_MOVE_KEY)
    move_data = move_data[1:-1].strip("'").split(",")
    print(move_data)
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

def process_moves():
    moves = get_move_data()
    for move in moves:
        start_time = datetime.fromtimestamp(move['start_time'])
        stop_time = datetime.fromtimestamp(move['stop_time'])
        coordinates = extract_coordinates_for_move(start_time, stop_time)
        if coordinates:
            save_move_coordinates(move['move_id'], coordinates) # save move txt
            #redis_client.rpush(MOVE_LIST_KEY, move['move_id'])
            # Remove the processed move from the Redis list
            redis_client.lrem(DEFINE_MOVE_KEY, 0, f"{move['move_id']}:{move['start_time']}:{move['stop_time']}")
            
            move_id = move['move_id']
            output_file = f"recordings/{move_id}.txt"
            interpolate(output_file, 0.2)

def replay_moves():
    while True:
        execute_flag = redis_client.get(EXECUTE_FLAG_KEY)
        if execute_flag == "1":
            move_id = redis_client.lpop(MOVE_LIST_KEY)
            if move_id:
                execute_move(move_id)
                redis_client.rpush(MOVE_EXECUTED_KEY, move_id)
            else:
                redis_client.set(EXECUTE_FLAG_KEY, "0")
        asyncio.sleep(0.1)

def execute_move(move_id):
    file_path = f"/Users/rheamalhotra/Desktop/robotics/react-genie-robotics/optitrack/recordings/{move_id}.txt"
    data = read_data(file_path)
    if data:
        publish_to_redis(data, rate_hz=30)

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

def publish_to_redis(data, rate_hz):
    """
    Publish each row of data to Redis, for panda to execute.
    """
    interval = 1.0 / rate_hz
    for row in data:
        timestamp = row.pop('timestamp', None)
        for key, value in row.items():
            new_key = "mmp_panda::" + key.split("::")[2]
            redis_client.set(new_key, value)
        asyncio.sleep(interval)

def test():
    move_id = input("enter move name: ")
    input("press enter to start recording")
    start = time.time()
    input("press enter to stop recording")
    stop = time.time()

    move = str(move_id) + ':' + str(start) + ':' + str(stop)

    redis_client.set(DEFINE_MOVE_KEY, [move])
    redis_client.set(MOVE_LIST_KEY, [move_id])
    redis_client.set(EXECUTE_FLAG_KEY, "1")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    # loop.run_until_complete(test())
    loop.create_task(process_moves())
    loop.create_task(replay_moves())
    loop.run_forever()
