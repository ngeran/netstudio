import logging
import os
from typing import Callable, Dict, List

from jnpr.junos import Device
from scripts.connect_to_hosts import connect_to_hosts, disconnect_from_hosts
from scripts.diagnostic_actions import ping_hosts as diag_ping_hosts
from scripts.interface_actions import configure_interfaces as configure_interface
from scripts.route_monitor import monitor_routes as perform_route_monitoring
from scripts.utils import load_yaml_file

logger = logging.getLogger(__name__)


def get_hosts():
    """Load hosts from hosts_data.yml or prompt for manual entry."""
    try:
        logger.info("DEBUG: Entering get_hosts")
        # Get the project directory (parent of scripts directory)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        vector_py_dir = os.getenv("VECTOR_PY_DIR", project_dir)
        hosts_file = os.path.join(vector_py_dir, "data/hosts_data.yml")

        # Prompt user to choose input method
        print("\nHow would you like to provide device information?")
        print("1. Load from inventory file (hosts_data.yml)")
        print("2. Enter manually")

        choice = input("Enter your choice (1/2): ").strip()

        if choice == "1":
            # Load from file
            hosts_data = load_yaml_file(hosts_file)
            if hosts_data is None:
                raise ValueError(f"Failed to load hosts file: {hosts_file}")
            hosts = hosts_data.get("hosts", [])
            # Support both 'ip_address' and 'host_ip' keys
            host_ips = [host.get("ip_address") or host.get("host_ip") for host in hosts]
            print(f"DEBUG: host_ips = {host_ips}")
            username = hosts_data.get("username", "admin")
            password = hosts_data.get("password", "password")
        elif choice == "2":
            # Manual entry
            hosts = []
            host_ips = []
            print("\nEnter device IPs (press Enter without input to finish):")
            while True:
                ip = input("Device IP: ").strip()
                if not ip:
                    break
                host_ips.append(ip)
                hosts.append({"host_ip": ip, "ip_address": ip, "host_name": ip})

            if not host_ips:
                raise ValueError("No devices entered")

            username = input("Username: ").strip()
            from getpass import getpass

            password = getpass("Password: ")
        else:
            raise ValueError("Invalid choice. Please select 1 or 2.")

        logger.info(f"Loaded hosts: {host_ips}, username: {username}")
        print(f"DEBUG: Loaded username: {username}, password: {'*' * len(password)}")
        return host_ips, hosts, username, password
    except Exception as e:
        logger.error(f"Error loading hosts: {e}")
        raise


def ping_hosts(
    username: str,
    password: str,
    host_ips: List[str],
    hosts: List[Dict],
    connect_to_hosts: Callable,
    disconnect_from_hosts: Callable,
):
    """Wrapper for the actual ping_hosts implementation in diagnostic_actions.py"""
    try:
        logger.info("Starting ping action (wrapper)")
        print("DEBUG: Starting ping_hosts wrapper")
        diag_ping_hosts(
            username=username,
            password=password,
            host_ips=host_ips,
            hosts=hosts,
            connect_to_hosts=connect_to_hosts,
            disconnect_from_hosts=disconnect_from_hosts,
        )
        logger.info("Ping action wrapper completed")
    except Exception as e:
        logger.error(f"Error in ping_hosts wrapper: {e}")
        raise


def configure_interfaces(
    username: str,
    password: str,
    host_ips: List[str],
    hosts: List[Dict],
    template_file: str = None,
):
    """Configure interfaces on all hosts."""
    try:
        logger.info("Starting interfaces action")
        print("DEBUG: Starting configure_interfaces")
        connections = []
        for host in host_ips:
            conn_list = connect_to_hosts(host, username, password)
            if conn_list:
                connections.extend(conn_list)
                host_data = next(h for h in hosts if h["ip_address"] == host)
                configure_interface(
                    conn_list[0], host_data.get("interfaces", []), template_file
                )
                logger.info(f"Interfaces configured for {host}")
        disconnect_from_hosts(connections)
        logger.info("Interfaces action completed")
    except Exception as e:
        logger.error(f"Error in configure_interfaces: {e}")
        raise


def run_monitor_routes_action(
    username: str,
    password: str,
    host_ips: List[str],
    hosts: List[Dict],
    connect_to_hosts: Callable,
    disconnect_from_hosts: Callable,
    connections: List[Device] = None,
):
    """Orchestrates the route monitoring action."""
    try:
        logger.info("Starting route_monitor action (orchestrator)")
        print("DEBUG: Entering run_monitor_routes_action")
        if connections is None:
            logger.info(
                f"DEBUG: Calling connect_to_hosts with hosts {host_ips}, username {username}"
            )
            print(
                f"DEBUG (run_monitor_routes_action): Connecting to hosts {host_ips} with username {username}"
            )
            connections = connect_to_hosts(host_ips, username, password)
            logger.info(
                f"DEBUG: connect_to_hosts returned {len(connections)} connections"
            )
            print(
                f"DEBUG (run_monitor_routes_action): Received {len(connections)} connections"
            )
        else:
            logger.info(f"DEBUG: Using provided connections: {len(connections)}")
            print(
                f"DEBUG (run_monitor_routes_action): Using {len(connections)} provided connections"
            )

        logger.info("DEBUG: Passing connections to perform_route_monitoring")
        print(
            f"DEBUG (run_monitor_routes_action): Passing {len(connections)} connections to perform_route_monitoring"
        )
        perform_route_monitoring(
            username=username,
            password=password,
            host_ips=host_ips,
            hosts=hosts,
            connect_to_hosts=connect_to_hosts,
            disconnect_from_hosts=disconnect_from_hosts,
            connections=connections,
        )
        disconnect_from_hosts(connections)
        logger.info("Route_monitor action orchestrator completed")
    except Exception as e:
        logger.error(f"Error in route_monitor orchestrator: {e}")
        print(f"ERROR (run_monitor_routes_action): {e}")
        raise
