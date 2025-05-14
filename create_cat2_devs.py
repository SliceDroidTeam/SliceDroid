from collections import defaultdict
import json
with open('rdevs.txt','r') as f:
    lines = f.readlines()
device_nodes = defaultdict(list)

# Uses r_dev to identify the device node
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
with open('regular_files.txt','r') as f:
    lines = f.readlines()
for line in lines:
    if 'callogger' in line:
        device_nodes['callogger'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))
    if 'contacts' in line:
        device_nodes['contacts'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))
    if 'sms' in line:
        device_nodes['sms'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))
    if 'calendar' in line:
        device_nodes['calendar'].append(f"{line.split(' ')[1]} - {line.split(' ')[2]}".replace('\n',''))

with open('cat2_devs_nothing2atest.json','w') as f:
    json.dump(device_nodes, f, indent=4)