from collections import defaultdict
import json
import os
import sys
# Path to the mappings directory where the JSON file will be saved
MAPPINGS_DIR = os.path.join("data", "mappings")

# Path to the data directory where the sh output files are located
DATA_DIR = os.path.join("data", "nodes_and_files_data")

#check if the directories exists, if not create them
if not os.path.exists(MAPPINGS_DIR):
    os.makedirs(MAPPINGS_DIR)
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

output_txt = os.path.join(MAPPINGS_DIR, 'cat2devs.txt')

# Use correct paths to the files
rdevs_path = os.path.join(DATA_DIR, 'rdevs.txt')
regular_files_path = os.path.join(DATA_DIR, 'regular_files.txt')

device_nodes = defaultdict(list)

# Uses r_dev to identify the device node
with open(rdevs_path, 'r') as f:
    lines = f.readlines()
print(lines)

for line in lines:
    if 'camera'== line.split(' ')[2] or 'camera'== line.split(' ')[3].removesuffix('\n'):
        device_nodes['camera'].append(line.split(' ')[1])
    if 'pcm' in line and line.split(' ')[0].endswith('c') and \
        ('audio'== line.split(' ')[3].removesuffix('\n') or 'audio'== line.split(' ')[2]):
        device_nodes['audio_in'].append(line.split(' ')[1])
    if 'nfc'== line.split(' ')[2] or 'nfc'== line.split(' ')[3].removesuffix('\n'):
        device_nodes['nfc'].append(line.split(' ')[1])
    if 'gps'== line.split(' ')[2] or 'gps'== line.split(' ')[3].removesuffix('\n'):
        device_nodes['gnss'].append(line.split(' ')[1])
    if 'bluetooth'== line.split(' ')[2] or 'bluetooth'== line.split(' ')[3].removesuffix('\n'):
        device_nodes['bluetooth'].append(line.split(' ')[1])

# Uses st_dev and i_node to identify the file
with open(regular_files_path, 'r') as f:
    lines = f.readlines()
    
for line in lines:
    if 'calllog' in line:
        device_nodes['callogger'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))
    if 'contacts' in line:
        device_nodes['contacts'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))
    if 'sms' in line:
        device_nodes['sms'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))
    if 'calendar' in line:
        device_nodes['calendar'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))

# Save the output to the mappings directory
with open(output_txt, 'w') as f:
    f.write(json.dumps(device_nodes, indent=4))

print(f"TXT file created at: {output_txt}")