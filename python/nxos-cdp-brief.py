#!/bin/env python
# Author: DS, shnosh.io

from __future__ import print_function
from cli import clid

import argparse
import json
import re
import sys

def check_natsort():
    """
    Return natsorted function if available, else None.
    """
    try:
        from natsort import natsorted
        return natsorted
    except ImportError:
        return None


def get_cdp_neighbors():
    """Return list of CDP neighbor dicts (normalized to a list)."""
    try:
        cdp_data = clid("show cdp neighbor detail")
        json_cdp_data = json.loads(cdp_data)["TABLE_cdp_neighbor_detail_info"]["ROW_cdp_neighbor_detail_info"]
    except (ValueError, KeyError, TypeError) as e:
        print("Error parsing CDP neighbors: {}".format(e))
        exit(0)

    # If more than one neighbor exists, a dict is built; otherwise a list is made.
    if isinstance(json_cdp_data, dict):
        return [json_cdp_data]
    elif isinstance(json_cdp_data, list):
        return list(json_cdp_data)
    else:
        print('Error - No CDP neighbors found.')
        sys.exit(0)


def parse_cdp_info(json_cdp_data, include_ver, include_plat):
    """Build the cdp_dict and neighbor_count from neighbor list."""
    i = 0
    cdp_dict = {}
    
    for entry in json_cdp_data:
        i += 1
        interface = entry["intf_id"]
        cdp_dict[interface, i] = {}

        # Trim local interface name
        local_intf = re.sub(r"(Eth|mgmt)[^\d]*([\d/]+)", r"\1\2", entry["intf_id"])
        cdp_dict[interface, i]["local_intf"] = local_intf

        # Trim neighbor hostname
        neighbor = re.split(r"[\.(]", entry["device_id"])[0]
        cdp_dict[interface, i]["neighbor"] = neighbor

        # Trim neighbor interface name
        neighbor_intf = re.sub(r"^(.{3})[^\d]*([\d/]+)", r"\1 \2", entry["port_id"])
        cdp_dict[interface, i]["neighbor_intf"] = neighbor_intf

        # Trim neighbor version info (optional)
        if include_ver:
            version_raw = entry.get("version", "")
            if "CCM" in version_raw:
                neighbor_ver = re.sub(r".*?CCM:([^ ,\n]*)", r"\1", version_raw)
            else:
                neighbor_ver = re.sub(r".*?version:* ([^ ,\n]*).*", r"\1", version_raw, flags=re.DOTALL | re.IGNORECASE)
            cdp_dict[interface, i]["neighbor_ver"] = neighbor_ver or "--"

        # Get neighbor platform (optional)
        if include_plat:
            platform_raw = entry.get("platform_id", "")
            neighbor_plat = re.sub(r"^cisco\s", "", platform_raw, flags=re.IGNORECASE)
            cdp_dict[interface, i]["neighbor_plat"] = neighbor_plat or "--"

        # Get neighbor IP address(es)
        mgmt_addr = entry.get('v4mgmtaddr')
        addr = entry.get('v4addr')

        # Normalize values
        if addr == mgmt_addr:
            addr = '(--)'
        elif addr == '0.0.0.0' or not addr:
            addr = '--'

        cdp_dict[interface, i]['neighbor_mgmtaddr'] = mgmt_addr or '--'
        cdp_dict[interface, i]['neighbor_addr'] = addr
    
    neighbor_count = i
    return cdp_dict, neighbor_count


def generate_cdp_table(include_ver, include_plat):
    cdp_dict, neighbor_count = parse_cdp_info(get_cdp_neighbors(), include_ver, include_plat)

    # Print header and custom CDP neighbor brief table.
    print(
        "Neighbors parsed: {}\n"
        "'L-Intf' = local interface\n"
        "'N-Intf' = neighbor interface\n".format(neighbor_count)
    )

    row_format = '%-8s -> %-22s %-14s %-16s %-16s'
    header_row = ('L-Intf', 'Neighbor', 'N-Intf', 'Mgmt-IPv4-Addr', 'IPv4-Addr')
    if include_plat and include_ver:
        row_format = row_format + ' %-20s %-20s'
        header_row = header_row + ('Platform', 'Version')
        dash_count = 115
    elif include_plat and not include_ver:
        row_format = row_format + ' %-20s'
        header_row = header_row + ('Platform',)
        dash_count = 95
    elif include_ver and not include_plat:
        row_format = row_format + ' %-20s'
        header_row = header_row + ('Version',)
        dash_count = 95
    else:
        dash_count = 80

    print(row_format % header_row)
    print('-' * dash_count)

    natsorted_fn = check_natsort()
    if natsorted_fn:
        sorted_neighbors = natsorted_fn(cdp_dict.items())
    else:
        sorted_neighbors = sorted(cdp_dict.items())

    for _, value in sorted_neighbors:
        curr_nei = (
            value["local_intf"],
            value["neighbor"],
            value["neighbor_intf"],
            value["neighbor_mgmtaddr"],
            value["neighbor_addr"],
        )
        if include_plat and include_ver:
            curr_nei = curr_nei + (value["neighbor_plat"], value["neighbor_ver"])
        elif include_plat and not include_ver:
            curr_nei = curr_nei + (value["neighbor_plat"],)
        elif include_ver and not include_plat:
            curr_nei = curr_nei + (value["neighbor_ver"],)
        print(row_format % curr_nei)


def main():
    parser = argparse.ArgumentParser(description="Cisco Nexus CDP Brief Generator.")
    parser.add_argument("-v", "--version", action="store_true", help="Include neighbor version in printout.")
    parser.add_argument("-p", "--platform", action="store_true", help="Include neighbor platform in printout.")
    args = parser.parse_args()
    include_ver = args.version
    include_plat = args.platform

    generate_cdp_table(include_ver, include_plat)


if __name__ == '__main__':
    main()