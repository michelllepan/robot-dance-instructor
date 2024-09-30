import redis
import numpy as np 
import ast 
import time 

# Define a function to parse each line of the file
def parse_line(line):
    # Split the line by tab character
    parts = line.strip().split('\t')
    
    # Extract the timestamp and the lists
    timestamp = parts[0]
    list1 = ast.literal_eval(parts[1])
    list2 = ast.literal_eval(parts[2])
    list3 = ast.literal_eval(parts[3])
    
    return timestamp, list1, list2, list3

ROBOT_DES_POS_KEY = "teleop::desired_pos"
ROBOT_DES_ORI_KEY = "teleop::desired_ori"
EE_POS_KEY = "sai2::panda::ee_pos"  # current op-space position
EE_ORI_KEY = "sai2::panda::ee_ori"  # current op-space orientation 
REPLAY_READY_KEY = "teleop::replay_ready"

# sample desired position and orientation
# desired_position = np.array([0.1, 0.2, 0.2])
# desired_orientation = np.array([ [-1, 0, 0], [0, 1, 0], [0, 0, -1] ])

client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Open the file and read its contents
position_data = []
with open('data2.txt', 'r') as file:
    for line in file:
        timestamp, list1, list2, list3 = parse_line(line)
        position_data.append(list2)
        # print("Timestamp:", timestamp)
        # print("List 1:", list1)
        # print("List 2:", list2)
        # print("List 3:", list3)
        # print()  # Print a blank line for separation

frequency = 25
interval = 1 / frequency 
interval = 0.232
for i in range(len(position_data)):
    print("Timestamp: ", i)
    start_time = time.time()
    current_position = position_data[i]
    current_position[2] = 0
    # current_position[1] = 0

    print(str(current_position))

    client.set(ROBOT_DES_POS_KEY, str(current_position))
    # client.set(ROBOT_DES_ORI_KEY, str(desired_orientation.tolist()))
    client.set(REPLAY_READY_KEY, "1")

    elapsed_time = time.time() - start_time
    time_to_sleep = interval - elapsed_time
        
    if time_to_sleep > 0:
        time.sleep(time_to_sleep)  # Sleep for the remaining time to maintain the desired frequency

