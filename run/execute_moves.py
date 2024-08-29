import redis
import time
import csv
from datetime import datetime, timedelta
import asyncio
import ast
import numpy as np
from scipy.spatial.transform import Rotation as R
from instructor.moves.interpolation import interpolate_between_moves, interpolate_file 
from instructor.utils import get_config, make_redis_client, read_log_array

cfg = get_config()
redis_client = make_redis_client()

DEFINE_MOVE_KEY = cfg["redis"]["keys"]["define_move"]
MOVE_LIST_KEY = cfg["redis"]["keys"]["move_list"]
EXECUTE_FLAG_KEY = cfg["redis"]["keys"]["execute_flag"]
MOVE_EXECUTED_KEY = cfg["redis"]["keys"]["move_executed"]

REALSENSE_PREFIX = cfg["redis"]["realsense_prefix"]

# rotate 90 counterclockwise around x
r1 = R.from_rotvec(np.pi/2 * np.array([1, 0, 0]))
# rotate 90 counterclockwise around z
r2 = R.from_rotvec(np.pi/2 * np.array([0, 0, 1]))
rot = r2 * r1

def apply_edits(file_path, speed, r, output_path):
    #Speed
    interpolate_file(file_path, cfg["smoothness"], frequency=cfg["rate"] * speed)
    
    #Rotation
    with open(file_path, 'r') as file:
        lines = file.readlines()

    header = lines[0].strip()
    data_lines = lines[1:]

    modified_lines = [header]

    for line in data_lines:
        parts = line.strip().split('\t')
        
        timestamp = parts[0]
        left_hand = eval(parts[1])
        right_hand = eval(parts[2])
        center_hips = eval(parts[3])
        center_shoulders = eval(parts[4])

        left_hand_rotated = np.dot(r, np.array(left_hand))
        right_hand_rotated = np.dot(r, np.array(right_hand))
        center_hips_rotated = np.dot(r, np.array(center_hips))
        center_shoulders_rotated = np.dot(r, np.array(center_shoulders))

        rotated_positions_str = [
            '[' + ', '.join(map(str, left_hand_rotated)) + ']',
            '[' + ', '.join(map(str, right_hand_rotated)) + ']',
            '[' + ', '.join(map(str, center_hips_rotated)) + ']',
            '[' + ', '.join(map(str, center_shoulders_rotated)) + ']'
        ]
        
        modified_line = '\t'.join([timestamp] + rotated_positions_str)
        modified_lines.append(modified_line)

    with open(output_path, 'w') as output_file:
        output_file.write('\n'.join(modified_lines))

    return output_path

def edit_move(file_path, move_edits):
    speed = 1
    r = np.eye(3)  # Start with an identity matrix (no rotation)
    output_path = file_path[:-4]  # Remove .txt from the end
    
    for edit in move_edits:
        output_path += f'_{edit}'
        if edit == 'slower':
            speed *= 0.5
        elif edit == 'faster':
            speed *= 2
        elif edit == 'rotate_left':
            r_left = R.from_rotvec(np.pi/2 * np.array([0, 0, 1]))  # Rotate 90 degrees around z-axis (counterclockwise)
            r = r_left.as_matrix() @ r
        elif edit == 'rotate_right':
            r_right = R.from_rotvec(-np.pi/2 * np.array([0, 0, 1]))  # Rotate 90 degrees around z-axis (clockwise)
            r = r_right.as_matrix() @ r
        elif edit == 'rotate_up':
            r_up = R.from_rotvec(np.pi/2 * np.array([1, 0, 0]))  # Rotate 90 degrees around x-axis (counterclockwise)
            r = r_up.as_matrix() @ r
        elif edit == 'rotate_down':
            r_down = R.from_rotvec(-np.pi/2 * np.array([1, 0, 0]))  # Rotate 90 degrees around x-axis (clockwise)
            r = r_down.as_matrix() @ r
    
    output_path += ".txt"
    return apply_edits(file_path, speed, r, output_path)


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

def publish_to_redis(data, move_edits, rate_hz=30):
    hand_coords = rot.apply(data[REALSENSE_PREFIX + "right_hand"])
    shoulder_coords = rot.apply(data[REALSENSE_PREFIX + "center_shoulders"])
    hip_coords = rot.apply(data[REALSENSE_PREFIX + "center_hips"])

    goal_coords = hand_coords - hip_coords

    torso_length = (shoulder_coords - hip_coords)[:,1:]
    torso_length = np.mean(np.linalg.norm(torso_length, axis=1))

    arm_length = 1.5 * torso_length
    goal_coords /= 2 * arm_length

    coords = np.clip(
        a=goal_coords,
        a_min=[0.49, -0.5, 0],
        a_max=[0.51, 0.5, 0.8],
    )

    for c in coords:
        redis_client.set("teleop::desired_pos", str(list(c)))
        time.sleep(1.0 / rate_hz)

def execute_move(move_id, move_edits, interpolated=True):
    print("Executing ", move_id, " with edits: ", move_edits)
    if interpolated:
        file_path = f"recordings/{move_id}_interpolated.txt"
    else: 
        file_path = f"recordings/{move_id}.txt"
    edited_file_path = edit_move(file_path, move_edits) # returns txt file
    data = read_log_array(edited_file_path)
    publish_to_redis(data, move_edits, rate_hz=cfg["rate"])

def replay_moves():
    while True:
        execute_flag = redis_client.get(EXECUTE_FLAG_KEY)
        if execute_flag == "1": 
            print("Begining move execution")
            move_list = redis_client.lrange(MOVE_LIST_KEY, 0, -1) # list of tuples
            for i in range(len(move_list)):
                move_id = move_list[i][0]
                move_edits = move_list[i][1]
                execute_move(move_id, move_edits)
                redis_client.rpush(MOVE_EXECUTED_KEY, move_list[i])
                if i + 1 < len(move_list):
                    next_move = move_list[i + 1]
                    interpolate_between_moves(move_list[i], next_move) #interpolate function needs to take in edits also
                    execute_move(str(move_id) + "_to_" + str(next_move[0]), False)
            print("Done with move execution!")
            redis_client.set(EXECUTE_FLAG_KEY, "0")
        
replay_moves()
