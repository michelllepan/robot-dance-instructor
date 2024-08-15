import redis
import time
import csv
from datetime import datetime, timedelta
import asyncio
import ast
from instructor.moves.interpolation import interpolate_between_moves 
from instructor.utils import get_config, make_redis_client

cfg = get_config()
redis_client = make_redis_client()

DEFINE_MOVE_KEY = cfg["redis"]["keys"]["define_move"]
MOVE_LIST_KEY = cfg["redis"]["keys"]["move_list"]
EXECUTE_FLAG_KEY = cfg["redis"]["keys"]["execute_flag"]
MOVE_EXECUTED_KEY = cfg["redis"]["keys"]["move_executed"]

def read_data(file_path):
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

def publish_to_redis(data, rate_hz=30):
    for row in data:
        timestamp = row.pop('timestamp', None)
        for key, value in row.items():
            if key.split("::")[2] != "right_hand": continue

            new_key = "teleop::desired_pos"

            # value = ",".join(value.split(",")[:-1]) + ", 0.5]"
            value = eval(value)
            value[1] += 0.1
            value[2] = 0.5
            value = str(value)
            # print(value) 
            redis_client.set(new_key, value)
        # print(timestamp)
        time.sleep(1.0 / rate_hz)

def execute_move(move_id, interpolated=True):
    print("executing ", move_id)
    if interpolated:
        file_path = f"recordings/{move_id}_interpolated.txt"
    else: 
        file_path = f"recordings/{move_id}.txt"
    data = read_data(file_path)
    if data:
        publish_to_redis(data, rate_hz=120)

def replay_moves():
    while True:
        execute_flag = redis_client.get(EXECUTE_FLAG_KEY)
        if execute_flag == "1": 
            print("Begining move execution")
            move_list = redis_client.lrange(MOVE_LIST_KEY, 0, -1)
            for i in range(len(move_list)):
                move_id = move_list[i]
                execute_move(move_id)
                redis_client.rpush(MOVE_EXECUTED_KEY, move_id)
                if i + 1 < len(move_list):
                    next_move = move_list[i + 1]
                    interpolate_between_moves(move_id, next_move)
                    execute_move(str(move_id) + "_to_" + str(next_move), False)
            print("Done with move execution!")
            redis_client.set(EXECUTE_FLAG_KEY, "0")
        
replay_moves()
