import redis
import time
import csv
from datetime import datetime, timedelta
import asyncio
import ast

# Redis configuration
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

DEFINE_MOVE_KEY = "robot::define_move" # single move : separated to be defined
MOVE_LIST_KEY = "robot::move_list" #list of move ids [move1, move2]
EXECUTE_FLAG_KEY = "robot::execute_flag" # binary 0 or 1 to execute all in move_list_key
MOVE_EXECUTED_KEY = "robot::move_executed" #A list of move_id executed

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

def publish_to_redis(data):
    for row in data:
        timestamp = row.pop('timestamp', None)
        for key, value in row.items():
            new_key = "mmp_panda::" + key.split("::")[2]
            redis_client.set(new_key, value)
        asyncio.sleep(1.0 / 30)

def execute_move(move_id):
    file_path = f"recordings/{move_id}.txt"
    data = read_data(file_path)
    if data:
        publish_to_redis(data, rate_hz=30)

def replay_moves():
    while True:
        execute_flag = redis_client.get(EXECUTE_FLAG_KEY)
        if execute_flag == "1":
            move_list_str = redis_client.get(MOVE_LIST_KEY)
            if move_list_str:
                move_list = ast.literal_eval(move_list_str)  # Convert from string to list
                for move in move_list:
                    execute_move(move)
                    executed_list_str = redis_client.get(MOVE_EXECUTED_KEY)
                    executed_list = ast.literal_eval(executed_list_str) if executed_list_str else []
                    executed_list.append(move)
                    redis_client.set(MOVE_EXECUTED_KEY, str(executed_list))
                redis_client.set(EXECUTE_FLAG_KEY, "0")
        asyncio.sleep(0.1)
        
replay_moves()
