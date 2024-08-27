#!/bin/env python
# Author: DS, shnosh.io
# pylint: disable=consider-using-f-string, missing-module-docstring, missing-function-docstring

import argparse
import json
import re
from cli import clid

parser = argparse.ArgumentParser(
    '\n\nNXOS CDP Brief.',
    description='Using -p and -v args simultaneously requires extra terminal width; try "terminal width 511".',
)
parser.add_argument(
    '-v', '--version', action='store_true', help='Include neighbor version in printout.',)
parser.add_argument(
    '-p', '--platform', action='store_true', help='Include neighbor platform in printout.')
args = parser.parse_args()
include_ver = args.version
include_plat = args.platform

# Try to import the natsort module for natural sorting.
try:
    from natsort import natsorted
    NATSORTED_AVAIL = True
except ImportError:
    NATSORTED_AVAIL = False

# Check for CDP neighbors.
try:
    return_data = clid('show cdp neighbor detail')
    json_data = json.loads(return_data)[
        'TABLE_cdp_neighbor_detail_info']['ROW_cdp_neighbor_detail_info']
except ValueError:
    print('No CDP neighbors found.')
    exit()

cdp = []
# If more than one neighbor exists, a dict is built; otherwise a list is made.
if isinstance(json_data, dict):
    cdp.append(json_data)
elif isinstance(json_data, list):
    for item in json_data:
        cdp.append(item)

i = 0
cdp_dict = {}
# Parse information from each CDP neighbor.
for entry in cdp:
    i += 1
    interface = entry['intf_id']
    cdp_dict[interface, i] = {}
    # Strip fat from local interface, add to dict.
    local_intf = re.sub(r'(Eth|mgmt)[^\d]*([\d/]+)', r'\1\2', entry['intf_id'])
    cdp_dict[interface, i]['local_intf'] = local_intf
    # Strip fat from neighbor hostname, add to dict.
    neighbor = re.split(r'[\.(]', entry['device_id'])[0]
    cdp_dict[interface, i]['neighbor'] = neighbor
    # Strip fat from neighbor interface, add to dict.
    neighbor_intf = re.sub(r'^(.{3})[^\d]*([\d/]+)', r'\1 \2', entry['port_id'])
    cdp_dict[interface, i]['neighbor_intf'] = neighbor_intf
    # Strip fat from neighor version, add to dict.
    if include_ver:
        if 'CCM' in entry['version']:
            neighbor_ver = re.sub(r'.*?CCM:([^ ,\n]*)', r'\1', entry['version'])
        else:
            neighbor_ver = re.sub(
                r'.*?version:* ([^ ,\n]*).*', r'\1', entry['version'], flags=re.DOTALL | re.IGNORECASE)
        cdp_dict[interface, i]['neighbor_ver'] = neighbor_ver
    # Get neighbor platform, add to dict.
    if include_plat:
        neighbor_plat = re.sub(r'^cisco\s', '', entry['platform_id'], flags=re.IGNORECASE)
        cdp_dict[interface, i]['neighbor_plat'] = neighbor_plat
    # Add neighbor IP address(es) to dict.
    try:
        MGMT_ADDR = entry['v4mgmtaddr']
    except ValueError:
        MGMT_ADDR = None
    try:
        ADDR = entry['v4addr']
        if ADDR == MGMT_ADDR:
            ADDR = '(--)'
        elif ADDR == '0.0.0.0':
            ADDR = '--'
    except ValueError:
        ADDR = None
    cdp_dict[interface, i]['neighbor_mgmtaddr'] = MGMT_ADDR or '--'
    cdp_dict[interface, i]['neighbor_addr'] = ADDR or '--'

# Print header and custom CDP neighbor brief table.
print("""CDP brief prints useful CDP neighbor information.

-v will include neighbor version information.
-p will include neighbor platform information.

* Use `grep` to filter output (N9K only).

Neighbors parsed: %s

'L-Intf' denotes local interface.
'N-Intf' denotes neighbor interface.\n\n""" % i)

ROW_FORMAT = '%-8s -> %-22s %-14s %-16s %-16s'
HEADER_ROW = ('L-Intf', 'Neighbor', 'N-Intf', 'Mgmt-IPv4-Addr', 'IPv4-Addr')
if include_plat and include_ver:
    ROW_FORMAT = ROW_FORMAT + ' %-20s %-20s'
    HEADER_ROW = HEADER_ROW + ('Platform', 'Version')
    DASH_COUNT = 115
elif include_plat and not include_ver:
    ROW_FORMAT = ROW_FORMAT + ' %-20s'
    HEADER_ROW = HEADER_ROW + ('Platform',)
    DASH_COUNT = 95
elif include_ver and not include_plat:
    ROW_FORMAT = ROW_FORMAT + ' %-20s'
    HEADER_ROW = HEADER_ROW + ('Version',)
    DASH_COUNT = 95
else:
    DASH_COUNT = 80

print(ROW_FORMAT % HEADER_ROW)
print('-'*DASH_COUNT)

if NATSORTED_AVAIL:
    sorted_neighbors = natsorted(cdp_dict.items())
else:
    sorted_neighbors = sorted(cdp_dict.items())

for key, value in sorted_neighbors:
    curr_nei = (value['local_intf'],
                value['neighbor'],
                value['neighbor_intf'],
                value['neighbor_mgmtaddr'],
                value['neighbor_addr'])
    if include_plat and include_ver:
        curr_nei = curr_nei + (value['neighbor_plat'], value['neighbor_ver'])
    elif include_plat and not include_ver:
        curr_nei = curr_nei + (value['neighbor_plat'],)
    elif include_ver and not include_plat:
        curr_nei = curr_nei + (value['neighbor_ver'],)
    print(ROW_FORMAT % curr_nei)
