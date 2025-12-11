import os
import logging
from typing import List, Dict
from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from jnpr.junos.exception import CommitError
from jinja2 import Environment, FileSystemLoader
from scripts.utils import load_yaml_file

logger = logging.getLogger(__name__)


def configure_interfaces(
    username: str,
    password: str,
    host_ips: List[str],
    hosts: List[Dict],
    connect_to_hosts: callable,
    disconnect_from_hosts: callable,
    connections: List[Device] = None,
):
    """Configure interfaces on devices using a Jinja2 template."""
    logger.info("Starting configure_interfaces")

    # Load template file from hosts_data.yml
    hosts_data_file = os.path.join(os.path.dirname(__file__), "../data/hosts_data.yml")
    hosts_data = load_yaml_file(hosts_data_file)
    template_file = hosts_data.get("template_file", "templates/interface_template.j2")
    logger.info(f"Using template_file: {template_file}")

    template_dir = os.path.join(os.path.dirname(__file__), "../")
    template_path = os.path.join(template_dir, template_file)

    if not os.path.exists(template_path):
        logger.error(f"Template file not found: {template_path}")
        print(f"Template file not found: {template_path}")
        return

    # Verify template content
    with open(template_path, "r") as f:
        template_content = f.read()
    if not template_content.strip():
        logger.error(f"Template file is empty: {template_path}")
        print(f"Template file is empty: {template_path}")
        return

    try:
        # Use provided connections
        if connections is None:
            logger.info("No connections provided, creating new connections")
            connections = connect_to_hosts(host_ips, username, password)
        if not connections:
            logger.error("No devices connected for interface configuration")
            print("No devices connected for interface configuration.")
            return

        host_lookup = {h["ip_address"]: h["host_name"] for h in hosts}
        print(f"Configuring interfaces for IPs: {host_ips}")

        # Setup Jinja2 environment
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(template_file)

        for dev in connections:
            hostname = host_lookup.get(dev.hostname, dev.hostname)
            try:
                # Find the host data for the current device
                host_data = next(
                    (h for h in hosts if h["ip_address"] == dev.hostname), None
                )
                if not host_data or "interfaces" not in host_data:
                    logger.error(f"No interface data for {hostname} ({dev.hostname})")
                    print(f"No interface data for {hostname} ({dev.hostname})")
                    continue

                # Prepare template variables
                template_vars = {"interfaces": host_data["interfaces"]}
                logger.info(f"Template vars for {hostname}: {template_vars}")

                # Render template
                config_data = template.render(**template_vars)
                logger.info(f"Rendered config for {hostname}:\n{config_data}")
                print(f"Config for {hostname} ({dev.hostname}):\n{config_data}")

                if not config_data.strip():
                    logger.error(f"Empty configuration for {hostname}")
                    print(f"Empty configuration for {hostname}")
                    continue

                # Apply configuration
                config = Config(dev)
                config.load(config_data, format="text")
                config.commit_check()
                config.commit()

                logger.info(f"Interface configured on {hostname} ({dev.hostname})")
                print(f"Interface configured on {hostname} ({dev.hostname})")

            except CommitError as e:
                logger.error(f"Commit error on {hostname} ({dev.hostname}): {e}")
                print(f"Commit error on {hostname} ({dev.hostname}): {e}")
            except Exception as e:
                logger.error(
                    f"Failed to configure interfaces on {hostname} ({dev.hostname}): {e}"
                )
                print(
                    f"Failed to configure interfaces on {hostname} ({dev.hostname}): {e}"
                )

    except Exception as e:
        logger.error(f"Error in configure_interfaces: {e}")
        print(f"Error in configure_interfaces: {e}")
    finally:
        # Rely on actions.py to disconnect
        pass
    logger.info("Finished configure_interfaces")
