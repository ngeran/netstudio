import os
import subprocess

import yaml
from jnpr.junos import Device
from jnpr.junos.exception import ConnectError


def load_yaml_file(file_path):
    """
    Load data from a YAML file.
    :param file_path: Path to the YAML file
    :return: Parsed YAML data or None if the file doesn't exist
    """
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return yaml.safe_load(file)
    return None


def save_yaml_file(data, file_path):
    """
    Save data to a YAML file.
    :param data: Python object to save
    :param file_path: Path to the YAML file
    """
    # Ensure the directory exists
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Save the YAML data to the file
    with open(file_path, "w") as file:
        yaml.safe_dump(data, file)


def is_device_reachable(ip_address, count=2, timeout=2):
    """
    Check if a device is reachable via ping.
    :param ip_address: The IP address of the device to ping.
    :param count: Number of ping attempts.
    :param timeout: Timeout for each ping in seconds.
    :return: True if the device is reachable, False otherwise.
    """
    try:
        # Use subprocess to execute the ping command
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", str(timeout), ip_address],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Return True if the ping command was successful
        return result.returncode == 0
    except Exception as e:
        print(f"Error checking reachability for {ip_address}: {e}")
        return False


def get_device_ips():
    """
    Get device IP addresses from the user.
    - User can choose to add IPs manually or load them from an inventory file.
    - Manual entries are saved to the inventory file for reuse.
    :return: List of devices with their type, hostname, and IP address
    """
    inventory_file = "data/upgrade_inventory.yml"
    devices = []

    print("How would you like to add device IP addresses?")
    print("1. Manually")
    print("2. Load from upgrade_inventory.yml")
    choice = input("Enter your choice (1/2): ")

    if choice == "1":
        # Manual entry
        while True:
            device_type = input("Enter device type (router/switch): ").lower()
            host_name = input("Enter host name: ")
            ip_address = input("Enter IP address: ")

            # Append the device details to the list
            devices.append(
                {
                    "device_type": device_type,
                    "host_name": host_name,
                    "ip_address": ip_address,
                }
            )

            # Ask if the user wants to add another device
            more = input("Do you want to add another device? (yes/no): ").lower()
            if more != "yes":
                break

        # Load existing inventory file if available, otherwise create a new one
        if os.path.exists(inventory_file):
            inventory_data = (
                load_yaml_file(inventory_file) or []
            )  # Initialize as empty list if None
        else:
            inventory_data = []

        # Add the new devices under a manual entry location
        inventory_data.append({"location": "Manual Entry", "devices": devices})
        save_yaml_file(inventory_data, inventory_file)

    elif choice == "2":
        # Load devices from YAML file
        inventory_data = load_yaml_file(inventory_file)
        if not inventory_data:
            print(f"Error: {inventory_file} not found or empty.")
            return []

        # Extract devices from inventory
        for location in inventory_data:
            devices.extend(location.get("devices", []))
    else:
        print("Invalid choice. Exiting.")
        return []

    # Confirm the list of devices with the user
    print("The following devices will be used:")
    for device in devices:
        print(
            f"{device['device_type'].capitalize()} - {device['host_name']} ({device['ip_address']})"
        )

    confirm = input("Do you confirm this list? (yes/no): ").lower()
    if confirm != "yes":
        print("Operation cancelled.")
        return []

    return devices


def display_menu(upgrade_data):
    """
    Display a menu to select platform and software version.
    :param upgrade_data: Parsed YAML data from upgrade_data.yml
    :return: Selected platform details as a dictionary
    """
    # Display list of platform series
    print("Select a platform series:")
    for idx, platform_series in enumerate(upgrade_data, start=1):
        print(f"{idx}. {platform_series['platform-series']}")

    # Get user's choice for platform series
    try:
        platform_choice = int(input("Enter your choice: ")) - 1
        selected_series = upgrade_data[platform_choice]
    except (IndexError, ValueError):
        print("Invalid selection. Exiting.")
        return None

    # Display available platforms and software versions
    print(f"Selected Platform Series: {selected_series['platform-series']}")
    print("Available platforms and versions:")
    for idx, platform in enumerate(selected_series["platform"], start=1):
        print(f"{idx}. {platform['platform']} - {platform['software']}")

    # Get user's choice for platform and version
    try:
        platform_version_choice = int(input("Enter your choice: ")) - 1
        selected_platform = selected_series["platform"][platform_version_choice]
    except (IndexError, ValueError):
        print("Invalid selection. Exiting.")
        return None

    return selected_platform


def main():
    """
    Main function to drive the workflow.
    - Prompts user for device IPs.
    - Checks reachability of devices.
    - Attempts SSH connection to reachable devices.
    """
    # Get the list of devices
    devices = get_device_ips()
    if not devices:
        return

    # Load upgrade data
    data_file = "data/upgrade_data.yml"
    upgrade_data = load_yaml_file(data_file)
    if not upgrade_data:
        print(
            f"Error: {data_file} not found or invalid. Please check the file and try again."
        )
        return

    # Display menu and get user selection
    selected_platform = display_menu(upgrade_data)
    if not selected_platform:
        print("No platform selected. Exiting.")
        return

    # Extract Junos image name
    image_name = selected_platform["junos"]

    # Iterate over each device and perform the reachability check
    for device in devices:
        host = device["ip_address"]

        print(f"Checking reachability for {host}...")
        if not is_device_reachable(host):
            print(f"Device {host} is not reachable. Skipping.")
            continue

        user = input(f"Enter the username for {host}: ")
        passwd = input(f"Enter the password for {host}: ")

        try:
            # Connect to the device
            with Device(host=host, user=user, passwd=passwd) as dev:
                print(f"Connected to {host} successfully.")
                # Additional pre-upgrade or post-upgrade tasks can be added here
        except ConnectError as e:
            print(f"Connection error for {host}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for {host}: {e}")


if __name__ == "__main__":
    main()
