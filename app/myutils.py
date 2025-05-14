import re
import json
import csv
import logging
import os

# Configure the logging system
#logging.basicConfig(
#    level=logging.DEBUG,  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
#    format='%(asctime)s - %(process)d - %(levelname)s - %(message)s',  # Log format
#    handlers=[
#        logging.StreamHandler()  # Output logs to the notebook cell
#    ]
#)
def are_equivalent(events1, events2):
    if len(events1) != len(events2):
        return False
    else:
        i = 0
        for i in range(0,len(events1)):
            e1 = events1[i]
            e2 = events2[i]
            if e1['event'] == e2['event']:
                if e1['event'] == ['inet_sock_set_state']:
                    for d in e1['details']:
                        if e1['details'][d] != e2['details]'][d]:
                            return False
                else:
                    for d in e1['details']:
                        if d in ['file', 'buf', 'pos', 'inode']:
                            continue
                        else:
                            if e1['details'][d] != e2['details'][d]:
                                return False
    return True

def save_to_file(parsed_events, output_file):
    # Save the list of events to a JSON file (for easy structured storage)
    with open(output_file, 'w') as f:
        json.dump(parsed_events, f, indent=4)

def load_file(input_file):
    with open(input_file, 'r') as f:
        return json.load(f)

def load_sensitive_resources(json_path='../data/mappings/cat2stdev.json'):
    import json
    with open(json_path, 'r') as f:
        return json.load(f)

def calculate_major_minor(dev_t):
    # Calculate major number: shift right by 20 bits and mask with 0xFFF (12 bits)
    major = (dev_t >> 20) & 0xFFF

    # Calculate minor number: lower 20 bits of dev_t
    minor = dev_t & 0xFFFFF

    return major, minor

def get_pid(tid, tgid, tgid_slicing):
    if tgid_slicing:
        pid = tgid
    else:
        pid = tid
    return pid

def parse_ftrace_log(file_path):
    # Regular expression to match Ftrace event log lines with TGID inside parentheses
    trace_pattern = re.compile(r'\s*(?P<process>((\S|\s)+|\<\.\.\.\>))-(?P<tid>\d+)\s+\(\s*(?P<tgid>(\d+|-------))\)\s+\[(?P<cpu>\d+)\]\s+(?P<flags>[\S]+)\s+(?P<timestamp>\d+\.\d+):\s+(?P<event>\S+):\s+(?P<details>.*)')

    # Regular expression to match key-value pairs inside the 'details' section
    detail_pattern = re.compile(r'(\S+)=(".*?"|\S+)')
    parsed_events = []  # List to store parsed events (sequence of events)

    with open(file_path, 'r') as f:
        for line in f:
            if len(line) > 1000:
                continue
            # Match the main trace line format
            match = trace_pattern.match(line)
            if match:
                # Extract main fields from the log line
                process = match.group('process')
                tid = int(match.group('tid'))      # Thread ID (TID) -> PID as integer
                try:
                    tgid = int(match.group('tgid'))    # Thread Group ID (TGID) as integer
                except ValueError:
                    tgid = -1 # When tgid is not known by the system use -1
                cpu = int(match.group('cpu'))      # CPU as integer
                flags = match.group('flags')
                timestamp = float(match.group('timestamp'))  # Timestamp as float
                event = match.group('event')
                details = match.group('details')

                # Parse the details section (key-value pairs)
                parsed_details = {}
                for detail_match in detail_pattern.finditer(details):
                    key, value = detail_match.groups()
                    if value.startswith("0x"):  # Handle hexadecimal values
                        parsed_details[key] = int(value, 16)  # Convert to integer
                    else:
                        try:
                            parsed_details[key] = int(value)  # Convert to integer if possible
                        except ValueError:
                            parsed_details[key] = value.strip('"')  # Keep as string if not int

                # Create a dictionary to store the parsed event
                parsed_event = {
                    "process": process,
                    "tid": tid,         # TID (PID) as integer
                    "tgid": tgid,       # TGID as integer
                    "cpu": cpu,         # CPU as integer
                    "flags": flags,     # Flags as string
                    "timestamp": timestamp,  # Timestamp as float
                    "event": event,     # Event name
                    "details": parsed_details  # Parsed key-value pairs
                }

                # Append the event to the list
                parsed_events.append(parsed_event)
            else:
                print(line)

    return parsed_events

def clean_event_list(elist):
    new_list = []
    for e in elist:
        # List cleaning operations
        new_e = dict()
        if e['event'] == 'write_probe' and e['details']['pathname'] == 'null' and e['details']['count'] > 999999:
            continue
        if e['event'] == 'ioctl_probe' and e['details']['pathname'] == '[userfaultfd]':
            continue
        if e['event'] == 'read_probe' and e['details']['pathname'] == 'cmdline':
            continue
        if e['event'] == 'write_probe' or e['event'] == 'read_probe' or e['event'] == 'ioctl_probe':
            if e['details']['pathname'] == '[eventfd]':
                continue
            new_e['event'] = e['event']
            new_e['details'] = dict()
            new_e['details']['k_dev'] = e['details']['k__dev']
            new_e['details']['s_dev'] = e['details']['s_dev_inode']
            new_e['details']['i_mode'] = e['details']['i_mode']
            new_e['details']['kuid'] = e['details']['kuid']
            new_e['details']['kgid'] = e['details']['kgid']
            #new_e['details']['pathname'] = e['details']['pathname']
        if e['event'] == 'inet_sock_set_state':
            new_e['event'] = e['event']
            new_e['details'] = dict()
            new_e['details']['oldstate'] = e['details']['oldstate']
            new_e['details']['newstate'] = e['details']['newstate']
            new_e['details']['dport'] = e['details']['dport']
            new_e['details']['daddr'] = e['details']['daddr']
            new_e['details']['daddrv6'] = e['details']['daddrv6']
        new_list.append(new_e)
    return new_list

def clean_event_list_withpath(elist):
    new_list = []
    for e in elist:
        new_e = dict()
        # List cleaning operations
        if e['event'] == 'write_probe' and e['details']['pathname'] == 'null' and e['details']['count'] > 999999:
            continue
        if e['event'] == 'ioctl_probe' and e['details']['pathname'] == '[userfaultfd]':
            continue
        if e['event'] == 'read_probe' and e['details']['pathname'] == 'cmdline':
            continue
        if e['event'] == 'write_probe' or e['event'] == 'read_probe' or e['event'] == 'ioctl_probe':
            if e['details']['pathname'] == '[eventfd]':
                continue
            new_e['event'] = e['event']
            new_e['details'] = dict()
            new_e['details']['k_dev'] = e['details']['k__dev']
            new_e['details']['s_dev'] = e['details']['s_dev_inode']
            new_e['details']['i_mode'] = e['details']['i_mode']
            new_e['details']['kuid'] = e['details']['kuid']
            new_e['details']['kgid'] = e['details']['kgid']
            new_e['details']['pathname'] = e['details']['pathname']
        if e['event'] == 'inet_sock_set_state':
            new_e['event'] = e['event']
            new_e['details'] = dict()
            new_e['details']['oldstate'] = e['details']['oldstate']
            new_e['details']['newstate'] = e['details']['newstate']
            new_e['details']['dport'] = e['details']['dport']
            new_e['details']['daddr'] = e['details']['daddr']
            new_e['details']['daddrv6'] = e['details']['daddrv6']
        new_list.append(new_e)
    return new_list

def clean_event_list_aggressive(elist):
    new_list = []
    for e in elist:
        # List cleaning operations
        new_e = dict()
        if e['event'] == 'write_probe' and e['details']['pathname'] == 'null' and e['details']['count'] > 999999:
            continue
        if (e['event'] == 'ioctl_probe' and (e['details']['pathname'] == 'binder' or e['details']['pathname'] == 'hwbinder')) or ((e['event'] == 'write_probe' or e['event'] == 'ioctl_probe') and 'binder' not in e['event']):
            continue
        if e['event'] == 'ioctl_probe' and e['details']['pathname'] == '[userfaultfd]':
            continue
        if e['event'] == 'read_probe' and e['details']['pathname'] == 'cmdline':
            continue
        if e['event'] == 'write_probe' or e['event'] == 'read_probe' or e['event'] == 'ioctl_probe':
            if e['details']['pathname'] == '[eventfd]':
                continue
            if e['details']['k__dev'] == 0 and e['details']['s_dev_inode'] < 1000:
                continue
            new_e['event'] = e['event']
            new_e['details'] = dict()
            new_e['details']['k_dev'] = e['details']['k__dev']
            new_e['details']['s_dev'] = e['details']['s_dev_inode']
            if 'ashmem' in e['details']['pathname']:
                new_e['details']['k_dev'] = 9999
                new_e['details']['s_dev'] = 9999
            new_e['details']['i_mode'] = e['details']['i_mode']
            new_e['details']['kuid'] = e['details']['kuid']
            new_e['details']['kgid'] = e['details']['kgid']
            #new_e['details']['pathname'] = e['details']['pathname']
        if e['event'] == 'inet_sock_set_state':
            new_e['event'] = e['event']
            new_e['details'] = dict()
            new_e['details']['oldstate'] = e['details']['oldstate']
            new_e['details']['newstate'] = e['details']['newstate']
            new_e['details']['dport'] = e['details']['dport']
            #new_e['details']['daddr'] = e['details']['daddr']
            #new_e['details']['daddrv6'] = e['details']['daddrv6']
        new_list.append(new_e)
    return new_list


def extract_instances(parsed_events):
    # Basic linear parsing method
    api_instances = dict()
    open_instances = dict()

    i = -1
    for e in parsed_events:
        i += 1
        if e['event'] == 'write_probe' and e['details']['pathname'] == 'null' and e['details']['count'] > 999999:
            api = e['details']['count']
            tid = e['tid']
            #if api not in code2api:
                #print(api, ' not found')
                #continue

            start = (api % 2 == 0)

            if start:
                if tid not in open_instances:
                    open_instances[tid] = dict()
                if api not in open_instances[tid]:
                    open_instances[tid][api] = []

                open_instances[tid][api].append(i)

            if not start:
                if tid not in open_instances or (api + 1) not in open_instances[tid]:
                    continue
                if open_instances[tid][api+1] == []:
                    continue
                last_instance_start = open_instances[tid][api+1].pop()
                if (api+1) not in api_instances:
                    api_instances[api+1] = []
                api_instances[api+1].append([last_instance_start, i])

    return(api_instances)
    print(len(api_instances))

def extract_relevant_instances_all(parsed_events, t_pid):
    # Basic linear parsing method
    api_instances = set()

    for e in parsed_events:
        if e['tgid'] == t_pid and e['event'] == 'write_probe' and e['details']['pathname'] == 'null' and e['details']['count'] > 99999:
            api = e['details']['count']
            tid = e['tid']

            #if api not in code2api:
                #print(api, ' not found')
                #continue

            start = (api % 2 == 0)

            if start:
                api_instances.add(api)
            else:
                api_instances.add(api+1)
    return(api_instances)

def slice_log(api_instances, parsed_events, tgid_slicing = False):
    # Double slicing algorithm to create in and out sets
    flows = dict()
    #ii = 0
    for api in api_instances:
        flows[api] = []

        #logger.info(str(ii) + ' ' + str(api) + ' ' + str(len(api_instances[api])))
        #ii += 1

        for instance in api_instances[api]:

            out_flows_slice = []
            in_flows_slice = []
            ioinstance = {'pid':0, 'command':0, 'in':[], 'out':[]}

            # Forward slicing for output operations (write or ioctl, which is considered "potential" read/write)
            #######################################################################
            # API start event
            ee = parsed_events[instance[0]]
            tgid = ee['tgid']
            tid = ee['tid']
            pid = get_pid(tid, tgid, tgid_slicing)
            api_pid = pid
            api_command = ee['process']

            # Relevent processes are tracked dynamically
            pid_set = {pid}
            binders = set()

            for line in range(instance[0],instance[1]+1):
                e = parsed_events[line]
                # Continue if an API start/end event is encountered
                if e['event'] == 'write_probe' and e['details']['pathname'] == 'null':
                    continue
                else:
                    tid = e['tid']
                    tgid = e['tgid']
                    event = e['event']

                    pid = get_pid(tid, tgid, tgid_slicing)

                    if pid in pid_set:
                        if event == 'binder_transaction':
                            binders.add(e['details']['transaction'])
                        elif (event == 'write_probe' and e['details']['pathname'] != 'null') or (event == 'ioctl_probe') or (event == 'inet_sock_set_state'):
                            # We consider socket state transitions both for input and output events
                            # Add event as output event for this instance
                            out_flows_slice.append(line)


                    # If a process receives a binder transaction originating from a tracked process, then the process also becomes tracked
                    if event == 'binder_transaction_received' and e['details']['transaction'] in binders:
                        if pid not in pid_set:
                            pid_set.add(pid)
                            #print('Added via binder')
                        binders.remove(e['details']['transaction'])

            # Backward slicing for input operations (read or ioctl, which is considered "potential" read/write)
            #######################################################################
            # API start event
            ee = parsed_events[instance[0]]
            tgid = ee['tgid']
            tid = ee['tid']
            pid = get_pid(tid, tgid, tgid_slicing)

            # Re-initialize variables
            pid_set = {pid}
            binders = set()

            for line in range(instance[1],instance[0]-1,-1):
                e = parsed_events[line]
                # Continue if an API start/end event is encountered
                if e['event'] == 'write_probe' and e['details']['pathname'] == 'null':
                    continue
                else:
                    tid = e['tid']
                    tgid = e['tgid']
                    event = e['event']

                    pid = get_pid(tid, tgid, tgid_slicing)

                    if pid in pid_set:
                        if event == 'binder_transaction_received':
                            binders.add(e['details']['transaction'])
                        elif event == 'read_probe' or event == 'ioctl_probe' or (event == 'inet_sock_set_state'):
                            # Add event as input event for this instance
                            in_flows_slice.append(line)
                            #print('Input event')


                    # If a process sends a binder transaction to a tracked process, then the process also becomes tracked - of course we are going in reverse now!
                    if event == 'binder_transaction' and e['details']['transaction'] in binders:
                        if pid not in pid_set:
                            pid_set.add(pid)
                            #print('Added via binder')
                        binders.remove(e['details']['transaction'])


            # After both passes, save the flows in the dictionary
            ioinstance['pid'] = api_pid
            ioinstance['command'] = api_command
            ioinstance['out'] = out_flows_slice.copy()
            ioinstance['in'] = in_flows_slice.copy()
            flows[api].append(ioinstance.copy())

    # Build compact in/out lists for saving and mass processing. Information needed includes: pid = ((tgid_slicing) ? tgid : tid), device (k_dev, s_dev), pathname, count (number of bytes)
    apis2io = dict()
    ii = 0
    for api in flows:
        #logger.info(str(ii) + ' ' + str(api) + ' ' + str(len(api_instances[api])))
        #ii += 1
        #jj = 0
        apis2io[api] = []
        for ioinstance in flows[api]:
            filtered_slice = dict()
            filtered_slice['pid'] = ioinstance['pid']
            filtered_slice['command'] = ioinstance['command']

            ###################################################################
            # We may want to merge the input and output events to create a single sequence. We do this based on the timestamps while removing duplicate ioctls
            # This is a new code block
            merged = []
            i = 0
            j = 0

            len_in = len(ioinstance['in'])
            len_out = len(ioinstance['out'])

            if len_in == 0 and len_out == 0:
                #filtered_slice['in'] = []
                #filtered_slice['out'] = []
                filtered_slice['merged'] = []
                apis2io[api].append(filtered_slice.copy())
                continue

            while (i < len_in) and (j < len_out):
                if ioinstance['in'][i] < ioinstance['out'][j]:
                    merged.append(ioinstance['in'][i])
                    i += 1
                else:
                    merged.append(ioinstance['out'][j])
                    j += 1

            merged = merged + ioinstance['in'][i:] + ioinstance['out'][j:]
            #if (jj % 1000 == 0):
            #    print(len(merged), jj)
            #jj += 1

            # Eliminate duplicate ioctl entries -- this needs improvement
            merged_unique = []
            for line in merged:
                if line not in merged_unique:
                    merged_unique.append(line)

            filtered_events = []
            for line in merged_unique:
                e = parsed_events[line]
                # Filter our remnant api logging if any, and binder transactions incl. their ioctl calls
                if (e['event'] == 'write_probe' and e['details']['pathname'] != 'null') or (e['event'] == 'ioctl_probe' and e['details']['pathname'] != 'binder' and e['details']['pathname'] != 'hwbinder') or (e['event'] != 'write_probe' and e['event'] != 'ioctl_probe' and 'binder' not in e['event']):
                    light_e = dict()
                    light_e['event'] = e['event']
                    light_e['details'] = e['details']
                    filtered_events.append(light_e.copy())
            filtered_slice['merged'] = filtered_events.copy()

            ###################################################################
            # New code block ends here.

            #for io in ['in', 'out']:
            #    lines = ioinstance[io]
            #    filtered_events = []
            #    for line in lines:
            #        e = parsed_events[line]
                    # Filter our remnant api logging if any, and binder transactions incl. their ioctl calls
            #        if (e['event'] == 'write_probe' and e['details']['pathname'] != 'null') or (e['event'] == 'ioctl_probe' and e['details']['pathname'] != 'binder' and e['details']['pathname'] != 'hwbinder') or (e['event'] != 'write_probe' and e['event'] != 'ioctl_probe' and 'binder' not in e['event']):
            #            light_e = dict()
            #            light_e['event'] = e['event']
            #            light_e['details'] = e['details']
            #            filtered_events.append(light_e.copy())
            #    filtered_slice[io] = filtered_events.copy()

            apis2io[api].append(filtered_slice.copy())
    return apis2io

def create_apis2uio(apis2io, withpath = False):
    apis2uio = dict()
    for api in apis2io:
        unique_instances = []
        for instance in apis2io[api]:
            simple_instance = dict()
            #simple_instance['in'] = clean_event_list(instance['in'])
            #simple_instance['out'] = clean_event_list(instance['out'])
            if not withpath:
                simple_instance['merged'] = clean_event_list(instance['merged'])
            else:
                simple_instance['merged'] = clean_event_list_withpath(instance['merged'])
            if unique_instances == []:
                simple_instance['count'] = 1
                unique_instances.append(simple_instance.copy())
            else:
                unique = True
                for ui in unique_instances:
                    #if are_equivalent(ui['in'], simple_instance['in']) and are_equivalent(ui['out'], simple_instance['out']):
                    if are_equivalent(ui['merged'], simple_instance['merged']):
                        unique = False
                        ui['count'] += 1
                        break
                if unique:
                    simple_instance['count'] = 1
                    unique_instances.append(simple_instance.copy())
        apis2uio[api] = unique_instances.copy()
    return apis2uio

def flatten_event(event):
    flat = {}
    for key, value in event.items():
        if key == "details" and isinstance(value, dict):
            for subkey, subvalue in value.items():
                flat[f"detail_{subkey}"] = subvalue
        else:
            flat[key] = value
    return flat

def export_events(events, csv_file_path, json_file_path):
    # Export events to JSON
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(events, json_file, indent=4, ensure_ascii=False)

    # Flatten events for CSV output
    flat_events = [flatten_event(event) for event in events]

    # Compute header columns as the union of all keys from all flattened events
    if flat_events:
        headers = sorted(set().union(*(event.keys() for event in flat_events)))
    else:
        headers = []

    # Export events to CSV
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(flat_events)