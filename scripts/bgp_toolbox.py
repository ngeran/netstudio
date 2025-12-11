import os
import time

import yaml
from jinja2 import Environment, FileSystemLoader
from jnpr.junos import Device
from jnpr.junos.exception import ConnectError, RpcError
from jnpr.junos.utils.config import Config
from tabulate import tabulate

# Helper function to load YAML data


def load_yaml(yaml_path):
    with open(yaml_path, "r") as file:
        return yaml.safe_load(file)


# Helper function to render Jinja2 templates
def render_template(template_path, data):
    env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
    template = env.get_template(os.path.basename(template_path))
    return template.render(data)


# Helper function to check if the reports folder exists, create it if it doesn't
def check_and_create_reports_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Created missing reports folder at: {folder_path}")
    else:
        print(f"Reports folder exists at: {folder_path}")


# Function to test if BGP is running
def is_bgp_running(dev):
    try:
        response = dev.rpc.get_bgp_summary_information()
        if response.findtext(".//bgp-peer") is not None:
            return True
        return False
    except RpcError:
        return False


# Option 1: Configure BGP using YAML and Jinja2
def configure_bgp(device, yaml_data, jinja_template):
    config_data = render_template(jinja_template, yaml_data)
    with Config(device) as cu:
        cu.load(config_data, format="text")
        cu.commit()
    print("BGP configuration applied successfully.")


# Option 2: Monitor BGP routing table
def monitor_bgp_routing_table(device, tables):
    headers = ["Table", "Prefix", "Next Hop", "AS Path"]
    data = []
    for table_name in tables:
        try:
            routes = device.rpc.get_route_information(table=table_name)
            for rt in routes.findall(".//rt"):
                prefix = rt.findtext("rt-destination")
                next_hop = rt.findtext("rt-entry/nh/to")
                as_path = rt.findtext("rt-entry/as-path")
                data.append([table_name, prefix, next_hop, as_path])
        except RpcError:
            continue
    print(tabulate(data, headers=headers, tablefmt="grid"))


# Option 3: Get BGP peer information including originated routes
def get_bgp_peer_info(device, report_path):
    headers = [
        "Peer Address",
        "State",
        "Received Routes",
        "Advertised Routes",
        "Originated Routes",
    ]
    data = []
    try:
        peers = device.rpc.get_bgp_summary_information()
        for peer in peers.findall(".//bgp-peer"):
            peer_address = peer.findtext("peer-address")
            state = peer.findtext("peer-state")

            if state == "Established":
                received_routes = peer.findtext("received-prefix-count")
                advertised_routes = peer.findtext("advertised-prefix-count")

                # Get originated routes for the peer
                originated_routes = []
                try:
                    originated_routes_rpc = device.rpc.get_route_information(
                        protocol="bgp", table="inet.0", active_path="yes"
                    )
                    for rt in originated_routes_rpc.findall(".//rt"):
                        as_path = rt.findtext("rt-entry/as-path")
                        if as_path and peer_address in as_path.split():
                            originated_routes.append(rt.findtext("rt-destination"))
                except RpcError:
                    print(
                        f"Failed to retrieve originated routes for peer {peer_address}"
                    )

                data.append(
                    [
                        peer_address,
                        state,
                        received_routes,
                        advertised_routes,
                        ", ".join(originated_routes),
                    ]
                )
    except RpcError:
        print("Error retrieving BGP peer summary.")

    with open(report_path, "w") as report_file:
        report_file.write(tabulate(data, headers=headers, tablefmt="grid"))
    print(tabulate(data, headers=headers, tablefmt="grid"))


# Option 4: Monitor BGP Peer Status across Multiple Devices and Refresh Every 5 Minutes
def get_bgp_group_peer_status(yaml_data):
    headers = [
        "Partner Name",
        "Peer IP",
        "Status",
        "Advertise Subnets",
        "Received Subnets",
    ]
    all_data = []

    for host in yaml_data["hosts"]:
        try:
            with Device(
                host=host["host_ip"],
                user=yaml_data["username"],
                passwd=yaml_data["password"],
            ) as dev:
                # Map peer IP to group (Partner Name)
                peer_to_group = {}
                try:
                    groups = dev.rpc.get_bgp_group_information()
                    for group in groups.findall(".//bgp-group"):
                        group_name = group.findtext("group-name")
                        for peer in group.findall(".//bgp-peer"):
                            peer_ip = peer.findtext("peer-address")
                            if peer_ip:
                                peer_to_group[peer_ip] = group_name
                except RpcError:
                    continue

                # Now get summary for each peer
                summary = dev.rpc.get_bgp_summary_information()
                for peer in summary.findall(".//bgp-peer"):
                    peer_ip = peer.findtext("peer-address")
                    state = peer.findtext("peer-state")
                    group_name = peer_to_group.get(peer_ip, "Unknown")

                    # Get advertised and received subnets
                    advertise_subnets = []
                    received_subnets = []
                    try:
                        advertised = dev.rpc.get_route_information(
                            protocol="bgp", peer=peer_ip, advertised=True
                        )
                        for rt in advertised.findall(".//rt"):
                            subnet = rt.findtext("rt-destination")
                            if subnet:
                                advertise_subnets.append(subnet)
                    except RpcError:
                        pass

                    try:
                        received = dev.rpc.get_route_information(
                            protocol="bgp", peer=peer_ip, received=True
                        )
                        print(etree.tostring(received, pretty_print=True).decode())
                        for rt in received.findall(".//rt"):
                            subnet = rt.findtext("rt-destination")
                            if subnet:
                                received_subnets.append(subnet)
                    except RpcError:
                        pass

                    all_data.append(
                        [
                            group_name,
                            peer_ip,
                            "UP" if state == "Established" else "DOWN",
                            ", ".join(advertise_subnets) if advertise_subnets else "-",
                            ", ".join(received_subnets) if received_subnets else "-",
                        ]
                    )
        except ConnectError as e:
            print(f"Could not connect to {host['host_name']}: {e}")
    return all_data, headers


def monitor_bgp_peer_status_refresh(yaml_data):
    while True:
        os.system("clear" if os.name == "posix" else "cls")
        refresh_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"BGP Peer Status (refreshes every 5 minutes) - Last refreshed: {refresh_time}\n"
        )
        data, headers = get_bgp_group_peer_status(yaml_data)
        print(tabulate(data, headers=headers, tablefmt="grid"))
        time.sleep(300)  # 5 minutes


def display_menu():
    menu_data = [
        ["1. Configure BGP"],
        ["2. Monitor BGP routing table"],
        ["3. Get BGP peer information"],
        ["4. Monitor BGP Peer Status"],
    ]
    print("Reports folder exists as: route/reports\n")
    print(tabulate(menu_data, headers=["Option", "Description"], tablefmt="grid"))
    choice = input("Enter your choice (1/2/3/4): ")
    return choice


def main():
    yaml_file = "data/hosts_data.yml"
    jinja_template = "templates/bgp_config.j2"
    reports_folder = "route/reports"
    report_path = os.path.join(reports_folder, "bgp_peer_info.txt")

    check_and_create_reports_folder(reports_folder)
    yaml_data = load_yaml(yaml_file)

    try:
        choice = display_menu()

        for host in yaml_data["hosts"]:
            print(f"Connecting to {host['host_name']} ({host['host_ip']})...")
            try:
                with Device(
                    host=host["host_ip"],
                    user=yaml_data["username"],
                    passwd=yaml_data["password"],
                ) as dev:
                    if not is_bgp_running(dev):
                        print(
                            f"BGP is not configured or running on {host['host_name']}."
                        )
                        continue

                    if choice == "1":
                        configure_bgp(dev, yaml_data, jinja_template)
                    elif choice == "2":
                        monitor_bgp_routing_table(dev, yaml_data["tables"])
                    elif choice == "3":
                        get_bgp_peer_info(dev, report_path)
            except ConnectError as e:
                print(f"Could not connect to {host['host_name']}: {e}")

        if choice == "4":
            monitor_bgp_peer_status_refresh(yaml_data)

    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting...")


if __name__ == "__main__":
    main()
