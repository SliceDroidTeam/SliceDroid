from collections import defaultdict
import json
import os
import sys
# Path to the mappings directory where the JSON file will be saved
MAPPINGS_DIR = "data/mappings"

# Path to the data directory where the sh output files are located
DATA_DIR = "outputs"

output_json = os.path.join(MAPPINGS_DIR, f'cat2_dev_{sys.argv[1]}.json')

# Use correct paths to the files
rdevs_path = os.path.join(DATA_DIR, 'rdevs.txt')
regular_files_path = os.path.join(DATA_DIR, 'regular_files.txt')

device_nodes = defaultdict(list)

# Uses r_dev to identify the device node
with open(rdevs_path, 'r') as f:
    lines = f.readlines()

for line in lines:
    #
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
    if 'callog' in line:
        device_nodes['callogger'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))
    if 'contacts' in line:
        device_nodes['contacts'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))
    if 'sms' in line:
        device_nodes['sms'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))
    if 'calendar' in line:
        device_nodes['calendar'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))

# Save the output to the mappings directory
with open(output_json, 'w') as f:
    json.dump(device_nodes, f, indent=4)

print(f"JSON file created at: {output_json}")