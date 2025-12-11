import os
from getpass import getpass

import yaml
from deepdiff import DeepDiff
from jnpr.junos.exception import ConnectAuthError, ConnectError, RpcTimeoutError
from jnpr.junos.factory.factory_loader import FactoryLoader
from tabulate import tabulate

from scripts.connect_to_hosts import connect_to_hosts

# Directories
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
# Base directory one level above scripts
BASE_DIR = os.path.dirname(SCRIPT_DIR)
# Data folder outside scripts directory
DATA_DIR = os.path.join(BASE_DIR, "data")
# State folder outside scripts directory
STATE_DIR = os.path.join(BASE_DIR, "state")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STATE_DIR, exist_ok=True)

# Custom table definitions
BGP_NEIGHBOR_TABLE = """
---
BGPNeighborTable:
  rpc: get-bgp-summary-information
  item: bgp-peer
  key: peer-address
  view: BGPNeighborView

BGPNeighborView:
  fields:
    peer_address: peer-address
    peer_state: peer-state
    peer_as: peer-as
    input_messages: input-messages
    output_messages: output-messages
    active_prefix_count: active-prefix-count
"""

ROUTE_TABLE = """
---
RouteTable:
  rpc: get-route-summary-information
  item: route-table
  key: table-name
  view: RouteView

RouteView:
  fields:
    name: table-name
    destinations: destination-count
    routes: route-count
    active_routes: active-route-count
    holddown: holddown-route-count
    hidden: hidden-route-count
    rib_route_count: rib-route-count
    fib_route_count: fib-route-count
    rib_unique_route_count: rib-unique-route-count
"""

factory_loader = FactoryLoader()
bgp_table = factory_loader.load(yaml.safe_load(BGP_NEIGHBOR_TABLE))["BGPNeighborTable"]
route_table = factory_loader.load(yaml.safe_load(ROUTE_TABLE))["RouteTable"]

# -----------------OSPF-CHECK-------------------------


def summarize_ospf_summary(device):
    """Summarize OSPF-related information dynamically using Junos PyEZ."""
    result = []

    try:
        # ================= OSPF Neighbor Information =================
        ospf_neighbors_raw = device.rpc.get_ospf_neighbor_information()
        ospf_neighbors_table = []

        for neighbor in ospf_neighbors_raw.xpath(".//ospf-neighbor"):
            neighbor_id = neighbor.findtext("neighbor-id", default="Unknown").strip()
            state = neighbor.findtext("ospf-neighbor-state", default="Unknown").strip()
            interface = neighbor.findtext("interface-name", default="Unknown").strip()
            ospf_neighbors_table.append([neighbor_id, state, interface])

        if ospf_neighbors_table:
            result.append("OSPF Neighbor Information:")
            result.append(
                tabulate(
                    ospf_neighbors_table,
                    headers=["Neighbor ID", "State", "Interface"],
                    tablefmt="grid",
                )
            )
        else:
            result.append("No OSPF neighbors found.")

        # ================= OSPF Interface Information =================
        ospf_interfaces_raw = device.rpc.get_ospf_interface_information()
        ospf_interfaces_table = []

        for interface in ospf_interfaces_raw.xpath(".//ospf-interface"):
            interface_name = interface.findtext("interface-name", default="Unknown").strip()
            state = interface.findtext("ospf-interface-state", default="Unknown").strip()
            ospf_interfaces_table.append([interface_name, state])

        if ospf_interfaces_table:
            result.append("OSPF Interface Information:")
            result.append(
                tabulate(
                    ospf_interfaces_table,
                    headers=["Interface Name", "State"],
                    tablefmt="grid",
                )
            )
        else:
            result.append("No OSPF interface information found.")
    except Exception as e:
        result.append(f"Error summarizing OSPF information: {e}")

    return "\n".join(result)


# -----------------SYSTEM-CHECK-------------------------


def summarize_system_check(device):
    """Summarize system state using various RPC calls."""
    result = []

    try:
        # Get software information
        software_info = device.rpc.get_software_information()
        software_version = software_info.findtext(
            ".//junos-version", default="Unknown"
        ).strip()
        result.append(f"Software Version: {software_version}")

        # Get core dumps
        core_dumps = device.rpc.get_system_core_dumps()
        core_dumps_table = []

        for core in core_dumps.xpath(".//core-dump-summary-information"):
            core_file = core.findtext("core-file-name", default="Unknown").strip()
            core_date = core.findtext("core-file-date", default="Unknown").strip()
            core_time = core.findtext("core-file-time", default="Unknown").strip()
            core_dumps_table.append([core_file, core_date, core_time])

        if core_dumps_table:
            result.append("\nCore Dumps:")
            result.append(
                tabulate(
                    core_dumps_table,
                    headers=["Core File", "Date", "Time"],
                    tablefmt="grid",
                )
            )
        else:
            result.append("\nCore Dumps: None found")

        # Get system alarms
        system_alarms = device.rpc.get_system_alarm_information()
        system_alarms_table = []

        for alarm in system_alarms.xpath(".//alarm-detail"):
            alarm_class = alarm.findtext("alarm-class", default="Unknown").strip()
            alarm_description = alarm.findtext(
                "alarm-description", default="Unknown"
            ).strip()
            alarm_time = alarm.findtext("alarm-time", default="Unknown").strip()
            system_alarms_table.append([alarm_class, alarm_description, alarm_time])

        if system_alarms_table:
            result.append("\nSystem Alarms:")
            result.append(
                tabulate(
                    system_alarms_table,
                    headers=["Class", "Description", "Time"],
                    tablefmt="grid",
                )
            )
        else:
            result.append("\nSystem Alarms: None")

        # Get chassis alarms using RPC
        try:
            chassis_alarms = device.rpc.get_chassis_alarm_information()
            chassis_alarms_table = []

            for alarm in chassis_alarms.xpath(".//alarm-detail"):
                alarm_class = alarm.findtext("alarm-class", default="Unknown").strip()
                alarm_description = alarm.findtext(
                    "alarm-description", default="Unknown"
                ).strip()
                chassis_alarms_table.append([alarm_class, alarm_description])

            if chassis_alarms_table:
                result.append("\nChassis Alarms:")
                result.append(
                    tabulate(
                        chassis_alarms_table,
                        headers=["Class", "Description"],
                        tablefmt="grid",
                    )
                )
            else:
                result.append("\nChassis Alarms: None")

        except Exception as e:
            result.append(f"\nError during chassis alarms check: {e}")

    except Exception as e:
        result.append(f"Error during system check: {e}")

    return "\n".join(result)


# -----------------LLDP-CHECK-------------------------


def summarize_lldp_neighbors(device):
    """Summarize LLDP neighbors dynamically using 'get_lldp_neighbors_information()'."""
    result = []
    lldp_neighbors_raw = (
        None  # Initialize the variable to avoid unbound variable errors
    )

    try:
        # Run the RPC command to get LLDP neighbors information
        lldp_neighbors_raw = device.rpc.get_lldp_neighbors_information()

        # Parse the XML response
        lldp_table = []

        # Navigate through the XML response to extract relevant data
        for neighbor in lldp_neighbors_raw.xpath(".//lldp-neighbor-information"):
            local_interface = neighbor.findtext(
                "lldp-local-interface", default="Unknown"
            ).strip()
            remote_interface = neighbor.findtext(
                "lldp-remote-port-description", default="Unknown"
            ).strip()
            remote_chassis_id = neighbor.findtext(
                "lldp-remote-chassis-id", default="Unknown"
            ).strip()
            remote_system_name = neighbor.findtext(
                "lldp-remote-system-name", default="Unknown"
            ).strip()

            # Add to the LLDP table
            lldp_table.append(
                [
                    local_interface,
                    remote_interface,
                    remote_chassis_id,
                    remote_system_name,
                ]
            )

        # Format LLDP Neighbors Table
        if lldp_table:
            result.append("LLDP Neighbors Table:")
            result.append(
                tabulate(
                    lldp_table,
                    headers=[
                        "Local Interface",
                        "Remote Interface",
                        "Remote Chassis ID",
                        "Remote System Name",
                    ],
                    tablefmt="grid",
                )
            )
        else:
            result.append("No LLDP neighbors found.")

    except Exception as e:
        result.append(f"Error summarizing LLDP neighbors: {e}")
    return "\n".join(result)


# -----------------INTERFACE-CHECK-------------------------


def summarize_interface_status(device):
    """Summarize interface status dynamically using 'get_interface_information(terse=True)'."""
    result = []
    interface_status_raw = (
        None  # Initialize the variable to avoid unbound variable errors
    )

    try:
        # Run the RPC command to get interface information
        interface_status_raw = device.rpc.get_interface_information(terse=True)

        # Parse the XML response
        interface_table = []

        # Define valid interface patterns
        valid_interfaces = ["ge-", "xe-", "ae0", "lo0", "em0"]

        # Navigate through the XML response to extract relevant data
        for interface in interface_status_raw.xpath(".//physical-interface"):
            # Get the interface name and normalize it
            interface_name = interface.findtext(
                "name", default="Unknown Interface"
            ).strip()

            # Check if the interface name starts with one of the valid patterns
            if not any(
                interface_name.lower().startswith(pattern)
                for pattern in valid_interfaces
            ):
                continue

            # Extract interface details
            admin_status = interface.findtext("admin-status", default="Unknown").strip()
            oper_status = interface.findtext("oper-status", default="Unknown").strip()

            # Add to the interface table
            interface_table.append(
                [
                    interface_name,
                    admin_status,
                    oper_status,
                ]
            )

        # Format Interface Table
        if interface_table:
            result.append("Filtered Interface Status Table:")
            result.append(
                tabulate(
                    interface_table,
                    headers=["Interface Name", "Admin Status", "Operational Status"],
                    tablefmt="grid",
                )
            )
        else:
            result.append("No matching interfaces found.")

    except Exception as e:
        result.append(f"Error summarizing interface status: {e}")
    return "\n".join(result)


# -----------------BGP-SUMMARY-CHECK-------------------------


def summarize_bgp_summary(device):
    """Summarize BGP peer states dynamically using Junos PyEZ."""
    result = []

    try:
        # Fetch BGP neighbor data dynamically using PyEZ
        bgp_neighbors = bgp_table(device)
        bgp_neighbors.get()

        # Initialize counters for BGP states
        bgp_states = {
            "Established": 0,
            "Idle": 0,
            "Active": 0,
            "Connect": 0,
            "OpenSent": 0,
            "OpenConfirm": 0,
            "Other": 0,  # For any unexpected states
        }

        # Collect detailed peer information
        peer_details = []

        # Iterate through neighbors and count states
        for neighbor in bgp_neighbors:
            state = neighbor.peer_state
            if state in bgp_states:
                bgp_states[state] += 1
            else:
                bgp_states["Other"] += 1

            # Add peer details (peer address and peer AS)
            peer_details.append([neighbor.peer_address, neighbor.peer_as, state])

        # Format the detailed peer table
        if peer_details:
            result.append("BGP Peer Details:")
            result.append(
                tabulate(
                    peer_details, headers=["Peer", "Peer AS", "State"], tablefmt="grid"
                )
            )

        # Format the BGP summary into a table
        bgp_table_data = [
            [state, count] for state, count in bgp_states.items() if count > 0
        ]
        result.append("BGP Peer Summary:")
        result.append(
            tabulate(bgp_table_data, headers=["State", "Count"], tablefmt="grid")
        )

        # Additional details (e.g., total peers and established percentage)
        total_peers = sum(bgp_states.values())
        established_peers = bgp_states.get("Established", 0)
        if total_peers > 0:
            established_percentage = (established_peers / total_peers) * 100
            result.append(f"Total Peers: {total_peers}")
            result.append(
                f"Established Peers: {established_peers} ({established_percentage:.2f}%)"
            )
        else:
            result.append("No BGP peers found.")
    except Exception as e:
        result.append(f"Error summarizing BGP peers: {e}")
    return "\n".join(result)


# ---------------------SUMMARY ROUTES--------------------------------


def summarize_routes(device):
    """Summarize routing table information dynamically using 'get_route_summary_information'."""
    result = []
    route_summary_raw = None  # Initialize the variable to avoid unbound variable errors

    try:
        # Run the RPC command to get route summary
        route_summary_raw = device.rpc.get_route_summary_information()

        # Parse the XML response
        protocol_table = []

        # Navigate through the XML response to extract relevant data
        for table in route_summary_raw.xpath(".//route-table"):
            table_name = table.findtext("table-name", default="Unknown Table")

            # Exclude inet.6 from the table
            if table_name.lower() == "inet.6":
                continue

            destination_count = int(table.findtext("destination-count", default="0"))
            total_route_count = int(table.findtext("total-route-count", default="0"))
            active_route_count = int(table.findtext("active-route-count", default="0"))

            # Extract protocols and their details
            for protocol in table.xpath(".//protocols"):
                protocol_name = protocol.findtext(
                    "protocol-name", default="Unknown Protocol"
                )
                protocol_route_count = int(
                    protocol.findtext("protocol-route-count", default="0")
                )
                protocol_active_count = int(
                    protocol.findtext("active-route-count", default="0")
                )

                # Add to the protocol table
                protocol_table.append(
                    [
                        table_name,
                        protocol_name,
                        destination_count,
                        total_route_count,
                        active_route_count,
                        protocol_route_count,
                        protocol_active_count,
                    ]
                )

        # Format Protocol Table
        if protocol_table:
            result.append("Routing Protocol Table:")
            result.append(
                tabulate(
                    protocol_table,
                    headers=[
                        "Table Name",
                        "Protocol",
                        "Destinations",
                        "Total Routes",
                        "Active Routes",
                        "Protocol Routes",
                        "Active Protocol Routes",
                    ],
                    tablefmt="grid",
                )
            )

    except Exception as e:
        result.append(f"Error summarizing routes: {e}")
    return "\n".join(result)


# --------------CAPTURE_DEVICE_STATE--------------------------------


def capture_device_state(ip, username, password):
    """Capture the state of a device with enhanced summaries."""
    dev = None
    state = None
    try:
        print(f"Checking device: {ip}")
        # Use connect_to_hosts to establish connection(s)
        devices = connect_to_hosts(ip, username, password)
        if not devices:
            print(f"Failed to connect to device: {ip}")
            return None
        # connect_to_hosts returns a list, use the first Device
        dev = devices[0]
        print(f"Connected to device: {ip}. Collecting data...")
        state = {
            "bgp_summary": summarize_bgp_summary(dev),
            "ospf_summary": summarize_ospf_summary(dev),
            "routes_summary": summarize_routes(dev),
            "interface_status": summarize_interface_status(dev),
            "lldp_neighbors": summarize_lldp_neighbors(dev),
            "system_check": summarize_system_check(dev),
        }
        print(f"Data collection successful for device: {ip}")
    except (ConnectAuthError, RpcTimeoutError, ConnectError) as error:
        print(f"Error while connecting to {ip}: {error}")
        with open("debug_log.txt", "a") as log_file:
            log_file.write(f"Device: {ip}, Error: {error}\n")
    except Exception as e:
        print(f"Unexpected error for device {ip}: {e}")
        with open("debug_log.txt", "a") as log_file:
            log_file.write(f"Device: {ip}, Unexpected Error: {e}\n")
    finally:
        if dev and dev.connected:
            dev.close()
        return state


def perform_state_check(label, devices, username, password, change_number):
    """Perform a state check and save the results."""
    state_file = os.path.join(STATE_DIR, f"{label}_{change_number}.yaml")
    txt_file = os.path.join(STATE_DIR, f"{label}_{change_number}.txt")
    all_states = {}

    for device in devices:
        state = capture_device_state(device, username, password)
        if state:
            all_states[device] = state
        else:
            print(f"Warning: No data collected for device {device}")

    if all_states:
        # Save as YAML
        with open(state_file, "w") as file:
            yaml.dump(all_states, file, default_flow_style=False)
        print(f"State saved to {state_file}")

        # Save as TXT
        with open(txt_file, "w") as file:
            for device, state in all_states.items():
                file.write(f"Device: {device}\n")
                for section, summary in state.items():
                    file.write(f"  Section: {section}\n")
                    if isinstance(summary, list):
                        file.write(
                            tabulate(summary, headers=["Key", "Value"], tablefmt="grid")
                        )
                    else:
                        file.write(f"    {summary}\n")
                    file.write("\n")
        print(f"State saved to {txt_file}")
    else:
        print("No valid data collected. State file not saved.")

    return state_file


def compare_states(pre_check_file, post_check_file):
    """Compare pre-check and post-check state files and report differences."""
    try:
        # Check if files exist
        if not os.path.exists(pre_check_file):
            print(f"Error: Pre-check file not found: {pre_check_file}")
            return
        if not os.path.exists(post_check_file):
            print(f"Error: Post-check file not found: {post_check_file}")
            return

        # Load the pre-check and post-check YAML files
        with open(pre_check_file, "r") as pre_file:
            pre_check_data = yaml.safe_load(pre_file)

        with open(post_check_file, "r") as post_file:
            post_check_data = yaml.safe_load(post_file)

        # Compare the two states using DeepDiff
        differences = DeepDiff(pre_check_data, post_check_data, ignore_order=True)

        if differences:
            print("Differences found between pre-check and post-check states:")
            print(differences)
        else:
            print("No differences found. The states are identical.")

    except Exception as e:
        print(f"Unexpected error: {e}")


def display_menu():
    """Display a menu for the user."""
    menu_options = [
        ["1", "Perform Pre-check"],
        ["2", "Perform Post-check"],
        ["3", "Compare Pre-check and Post-check"],
    ]
    print(tabulate(menu_options, headers=["Option", "Description"], tablefmt="grid"))
    return input("Enter your choice (1/2/3): ").strip()


def main():
    try:
        user_choice = display_menu()
        change_number = input("Enter Change Number: ").strip()
        if user_choice == "1":
            username = input("Enter username: ")
            password = getpass("Enter password: ")
            devices = input("Enter device IPs (comma-separated): ").split(",")
            perform_state_check("pre_check", devices, username, password, change_number)
        elif user_choice == "2":
            username = input("Enter username: ")
            password = getpass("Enter password: ")
            devices = input("Enter device IPs (comma-separated): ").split(",")
            perform_state_check(
                "post_check", devices, username, password, change_number
            )
        elif user_choice == "3":
            pre_check_file = os.path.join(STATE_DIR, f"pre_check_{change_number}.yaml")
            post_check_file = os.path.join(
                STATE_DIR, f"post_check_{change_number}.yaml"
            )
            compare_states(pre_check_file, post_check_file)
        else:
            print("Invalid choice. Exiting.")
    except KeyboardInterrupt:
        print("\nOperation cancelled by the user. Exiting gracefully.")
    except Exception as e:
        print(f"Error Occured: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("Main function completed.")


if __name__ == "__main__":
    main()
