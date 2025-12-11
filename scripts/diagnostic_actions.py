import os
from datetime import datetime
from contextlib import contextmanager
import signal
import logging
from typing import List
from jnpr.junos import Device

logger = logging.getLogger(__name__)


# Timeout context for RPC calls
@contextmanager
def timeout(seconds):
    def signal_handler(signum, frame):
        raise TimeoutError("Operation timed out")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def ping_hosts(
    username: str,
    password: str,
    host_ips: List[str],
    hosts: List[dict],
    connect_to_hosts: callable,
    disconnect_from_hosts: callable,
    connections: List[Device] = None,
    single_check: bool = False,
):
    """Verify reachability by pinging hosts from each device and generate a report."""
    logger.info("Starting ping_hosts")
    report_dir = os.path.join(os.path.dirname(__file__), "../reports")
    os.makedirs(report_dir, exist_ok=True)

    local_connections = []
    try:
        # Use provided connections if available; otherwise, connect
        if connections is None:
            logger.info("No connections provided, creating new connections")
            connections = []
            # The issue might be here:
            conn_list = connect_to_hosts(host_ips, username, password)
            if conn_list:
                connections.extend(conn_list)
            local_connections = connections
        if not connections:
            logger.error("No devices connected for ping verification")
            print("No devices connected for ping verification.")
            return

        connected_ips = [dev.hostname for dev in connections]
        # Support both 'ip_address' and 'host_ip' keys, and 'host_name' or use IP as fallback
        host_lookup = {
            h.get("ip_address") or h.get("host_ip"): h.get(
                "host_name", h.get("ip_address") or h.get("host_ip")
            )
            for h in hosts
        }
        reachable = []
        unreachable = []

        for dev in connections:
            source_host = host_lookup.get(dev.hostname, dev.hostname)
            for target_ip in connected_ips:
                if target_ip == dev.hostname:
                    continue
                target_host = host_lookup.get(target_ip, target_ip)
                try:
                    with timeout(5):
                        ping_result = dev.rpc.cli(
                            f"ping {target_ip} count 4", format="text"
                        )
                    ping_output = ping_result.text
                    if " 0% packet loss" in ping_output:
                        reachable.append(
                            f"{source_host} ({dev.hostname}) can reach {target_host} ({target_ip})"
                        )
                    else:
                        unreachable.append(
                            f"{source_host} ({dev.hostname}) cannot reach {target_host} ({target_ip})"
                        )
                except TimeoutError:
                    unreachable.append(
                        f"{source_host} ({dev.hostname}) ping to {target_host} ({target_ip}) timed out"
                    )
                except Exception as error:
                    unreachable.append(
                        f"{source_host} ({dev.hostname}) ping to {target_ip} failed: {error}"
                    )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report = f"Ping Verification Report - {timestamp}\n{'=' * 50}\n"
        report += "\nReachable:\n"
        for entry in reachable:
            report += f"  - {entry}\n"
        report += "\nUnreachable:\n"
        for entry in unreachable:
            report += f"  - {entry}\n"

        report_file = os.path.join(report_dir, f"ping_report_{timestamp}.txt")
        with open(report_file, "w") as f:
            f.write(report)
        logger.info(f"Ping report saved to {report_file}")
        print(f"Ping report saved to {report_file}")

    except KeyboardInterrupt:
        logger.info("Ping action interrupted by user")
        print("Ping action interrupted by user.")
        raise
    except Exception as e:
        logger.error(f"Error in ping_hosts: {e}")
        print(f"Error in ping_hosts: {e}")
    finally:
        if local_connections:
            logger.info("Disconnecting local connections")
            disconnect_from_hosts(local_connections)
    logger.info("Finished ping_hosts")
