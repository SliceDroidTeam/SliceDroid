from collections import defaultdict
import json
import os

# Path to the mappings directory where the JSON file will be saved
MAPPINGS_DIR = "data/mappings"

# Path to the data directory where the sh output files are located
DATA_DIR = "outputs"

# Use correct paths to the files
rdevs_path = os.path.join(DATA_DIR, 'rdevs.txt')
regular_files_path = os.path.join(DATA_DIR, 'regular_files.txt')

device_nodes = defaultdict(list)

# Uses r_dev to identify the device node
with open(rdevs_path, 'r') as f:
    lines = f.readlines()

for line in lines:
    if 'v4l' in line or 'video' in line:
        device_nodes['camera'].append(line.split(' ')[1].replace('\n',''))
    if 'pcm' in line and line.split(' ')[0].endswith('c'):
        device_nodes['audio_in'].append(line.split(' ')[1].replace('\n',''))
    if 'nfc' in line:
        device_nodes['nfc'].append(line.split(' ')[1].replace('\n',''))
    if 'gnss' in line or 'gps' in line:
        device_nodes['gnss'].append(line.split(' ')[1].replace('\n',''))
    if 'rfkill' in line:
        device_nodes['bluetooth'].append(line.split(' ')[1].replace('\n',''))

# Uses st_dev and i_node to identify the file
with open(regular_files_path, 'r') as f:
    lines = f.readlines()
    
for line in lines:
    if 'callog' in line:
        device_nodes['callogger'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))
    if 'contacts' in line:
        device_nodes['contacts'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))
    if 'sms' in line:
        device_nodes['sms'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))
    if 'calendar' in line:
        device_nodes['calendar'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))

# Save the output to the mappings directory
output_json = os.path.join(MAPPINGS_DIR, 'cat2_dev.json')
with open(output_json, 'w') as f:
    json.dump(device_nodes, f, indent=4)

print(f"JSON file created at: {output_json}")