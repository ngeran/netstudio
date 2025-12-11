import logging
import os
from scripts.actions import ping_hosts, get_hosts, run_monitor_routes_action
from scripts.interface_actions import configure_interfaces as configure_interface
from scripts.utils import load_yaml_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="network_automation.log",
)
logger = logging.getLogger(__name__)


def display_menu(actions):
    """Display a menu of actions and return the user's choice."""
    print("Select an action:")
    print("----------------------------------------")
    print("| Option | Action                  |")
    print("----------------------------------------")
    for i, action in enumerate(actions, 1):
        display_name = action.get("display_name", action["name"])
        print(f"| {i:<6} | {display_name:<22} |")
    print("----------------------------------------")
    max_retries = 5
    retries = 0
    while retries < max_retries:
        try:
            raw_input = input(f"Enter your choice (1-{len(actions)}): ").strip()
            logger.info(f"Raw input received: '{raw_input}'")
            if not raw_input:
                logger.error("Empty input received")
                print(
                    f"Invalid choice. Please enter a number between 1 and {len(actions)}"
                )
                retries += 1
                continue
            choice = int(raw_input)
            if 1 <= choice <= len(actions):
                logger.info(f"Valid choice selected: {choice}")
                return choice
            logger.error(f"Choice out of range: {choice}")
            print(f"Invalid choice. Please enter a number between 1 and {len(actions)}")
            retries += 1
        except ValueError:
            logger.error(f"Non-numeric input: '{raw_input}'")
            print(f"Invalid choice. Please enter a number between 1 and {len(actions)}")
            retries += 1
        except EOFError:
            logger.error("EOF received during input")
            print(
                f"Input interrupted. Please enter a number between 1 and {len(actions)}"
            )
            retries += 1
    logger.error(f"Max retries ({max_retries}) reached in display_menu")
    print("Too many invalid attempts. Exiting.")
    return None


def main(action_name=None):
    """Main function to execute network automation actions."""
    try:
        logger.info(f"Executing action: {action_name}")
        if not action_name:
            logger.error("No action name provided")
            print("Error: No action name provided")
            return

        # Load actions to get template_file
        # Get the project directory (parent of scripts directory)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        actions_file = os.path.join(
            os.getenv("VECTOR_PY_DIR", project_dir), "data/actions.yml"
        )
        actions_data = load_yaml_file(actions_file)
        if actions_data is None:
            logger.error(f"Failed to load actions file: {actions_file}")
            print(f"Error: Failed to load actions file: {actions_file}")
            return
        action_info = next(
            (a for a in actions_data.get("actions", []) if a["name"] == action_name), {}
        )

        # Get hosts data
        host_ips, hosts, username, password = get_hosts()

        # Import connect_to_hosts and disconnect_from_hosts here
        from scripts.connect_to_hosts import connect_to_hosts
        from scripts.actions import disconnect_from_hosts

        # Map action names to functions
        action_map = {
            "ping": lambda: ping_hosts(
                username=username,
                password=password,
                host_ips=host_ips,
                hosts=hosts,
                connect_to_hosts=connect_to_hosts,
                disconnect_from_hosts=disconnect_from_hosts,
            ),
            "interfaces": lambda: configure_interface(
                username=username,
                password=password,
                host_ips=host_ips,
                hosts=hosts,
                connect_to_hosts=connect_to_hosts,
                disconnect_from_hosts=disconnect_from_hosts,
                connections=None,
            ),
            "route_monitor": lambda: run_monitor_routes_action(
                username=username,
                password=password,
                host_ips=host_ips,
                hosts=hosts,
                connect_to_hosts=connect_to_hosts,
                disconnect_from_hosts=disconnect_from_hosts,
            ),
        }

        action_func = action_map.get(action_name)
        if not action_func:
            logger.error(f"Unknown action: {action_name}")
            print(f"Error: Unknown action {action_name}")
            return

        # Execute the action
        action_func()
        logger.info(f"Completed action: {action_name}")

    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
