import getpass
import time
from datetime import datetime
from typing import Dict, List, Optional

from jnpr.junos.exception import RpcError
from tabulate import tabulate

# Import connect_to_hosts from sibling script
try:
    # If run as part of the package
    from scripts.connect_to_hosts import connect_to_hosts, disconnect_from_hosts
except ImportError:
    # If run as standalone from the same directory
    from connect_to_hosts import connect_to_hosts, disconnect_from_hosts


def get_all_route_tables(device):
    """Retrieve all routing tables from the device using PyEZ."""
    try:
        route_tables = device.rpc.get_route_information(table="all", extensive=True)
        tables = {}
        for table in route_tables.findall(".//route-table"):
            table_name = table.findtext("table-name")
            routes = []
            for route in table.findall("rt"):
                prefix = route.findtext("rt-destination")
                protocol = route.findtext("rt-entry/protocol-name")
                nh = route.find(".//nh")
                next_hop = nh.findtext("to") if nh is not None else "-"
                as_path = "-"
                # Extract AS-Path if BGP
                if protocol and protocol.lower() == "bgp":
                    as_path_elem = route.find(".//as-path")
                    as_path = as_path_elem.text if as_path_elem is not None else "-"
                routes.append(
                    {
                        "prefix": prefix,
                        "next_hop": next_hop,
                        "protocol": protocol,
                        "as_path": as_path,
                    }
                )
            tables[table_name] = routes
        return tables
    except RpcError as e:
        print(f"ERROR (rpc): Failed to retrieve routing tables: {e}")
        return {}


def routes_to_dict(routes):
    """Create a dict for fast lookup: (prefix, next_hop, protocol, as_path) as key"""
    route_dict = {}
    for r in routes:
        key = (r["prefix"], r["next_hop"], r["protocol"], r["as_path"])
        route_dict[key] = r
    return route_dict


def compare_routes(old: List[dict], new: List[dict]):
    """Return (added, removed) route lists."""
    old_dict = routes_to_dict(old)
    new_dict = routes_to_dict(new)
    added = [v for k, v in new_dict.items() if k not in old_dict]
    removed = [v for k, v in old_dict.items() if k not in new_dict]
    return added, removed


def print_table(table_name, routes):
    """Print routing table using tabulate."""
    headers = ["Prefix", "Next-hop", "Protocol", "AS-Path"]
    table = [[r["prefix"], r["next_hop"], r["protocol"], r["as_path"]] for r in routes]
    print(f"\nRouting Table: {table_name}")
    print(tabulate(table, headers=headers, tablefmt="fancy_grid"))


def append_report(report_path, device_ip, table_name, added, removed):
    """Append changes to the report file."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(report_path, "a") as f:
        f.write(f"\n[{now}] Device: {device_ip} Table: {table_name}\n")
        if added:
            f.write("  Added routes:\n")
            for r in added:
                f.write(
                    f"    + {r['prefix']:20} {r['next_hop']:20} {r['protocol']:10} {r['as_path']}\n"
                )
        if removed:
            f.write("  Removed routes:\n")
            for r in removed:
                f.write(
                    f"    - {r['prefix']:20} {r['next_hop']:20} {r['protocol']:10} {r['as_path']}\n"
                )
        if not (added or removed):
            f.write("  No changes detected.\n")


def prompt_user():
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    ips = input("Device IP(s) (comma or space separated): ")
    ip_list = [i.strip() for i in ips.replace(",", " ").split() if i.strip()]
    interval = input("Polling interval (minutes, default 1): ")
    try:
        interval = int(interval)
    except Exception:
        interval = 1
    return username, password, ip_list, interval


def monitor_routes(username, password, ip_list, interval):
    connections = connect_to_hosts(ip_list, username, password)
    if not connections:
        print("No devices connected. Exiting.")
        return

    previous_tables: Dict[str, Dict[str, List[dict]]] = {}
    report_files = {
        dev.hostname: f"route_changes_{dev.hostname}.txt" for dev in connections
    }

    try:
        while True:
            for dev in connections:
                device_ip = dev.hostname
                print(f"\n========== Device: {device_ip} ==========")
                current_tables = get_all_route_tables(dev)
                prev_tables = previous_tables.get(device_ip, {})
                for table_name, routes in current_tables.items():
                    print_table(table_name, routes)
                    prev_routes = prev_tables.get(table_name, [])
                    added, removed = compare_routes(prev_routes, routes)
                    append_report(
                        report_files[device_ip], device_ip, table_name, added, removed
                    )
                previous_tables[device_ip] = current_tables
            print(f"\nSleeping for {interval} minute(s)...\n")
            time.sleep(interval * 60)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
    finally:
        disconnect_from_hosts(connections)


def main(
    username: Optional[str] = None,
    password: Optional[str] = None,
    ip_list: Optional[List[str]] = None,
    interval: Optional[int] = 1,
):
    """Main entry point for both standalone and launcher.py usage."""
    if username is None or password is None or not ip_list:
        username, password, ip_list, interval = prompt_user()
    monitor_routes(username, password, ip_list, interval)


if __name__ == "__main__":
    main()
root@ORIENGWANDJEX01:RE:0% cat test_connect.py
from scripts.connect_to_hosts import connect_to_hosts

hosts = ["10.177.102.37", "10.177.102.38"]
connections = connect_to_hosts(hosts, "admin", "P@ssw0rd")
print(f"Connections: {len(connections)}")
