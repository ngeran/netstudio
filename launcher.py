import logging
import os
import sys
import traceback

# Set the project directory and add it to sys.path before imports
project_dir = os.path.abspath(os.path.dirname(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Configure logging early for debugging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=os.path.join(project_dir, "network_automation.log"),
)
logger = logging.getLogger(__name__)
logger.info(f"sys.path: {sys.path}")

# Module-level imports at the top
try:
    from scripts import bgp_toolbox, config_toolbox, route_monitor, state_capture
    from scripts.code_upgrade import code_upgrade
    from scripts.network_automation import main as network_automation_main
    from scripts.utils import load_yaml_file
    from tabulate import tabulate
except ImportError as e:
    logger.error(f"Import error: {e}")
    raise


def display_menu(actions):
    """Display a menu of actions and return the user's choice."""
    menu_options = []
    for i, action in enumerate(actions, 1):
        display_name = action.get("display_name", action["name"])
        menu_options.append([str(i), display_name])
    print(tabulate(menu_options, headers=["Option", "Action"], tablefmt="grid"))
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
        except KeyboardInterrupt:
            logger.info("Program interrupted by user (Ctrl+C)")
            print("\nProgram interrupted by user. Exiting.")
            sys.exit(0)
    logger.error(f"Max retries ({max_retries}) reached in display_menu")
    print("Too many invalid attempts. Exiting.")
    return None


def display_execution_mode_menu():
    """Display execution mode menu and return the user's choice."""
    modes = [["1", "Execute Locally"], ["2", "Push to Github"]]
    print("\nChoose Execution Mode:")
    print(tabulate(modes, headers=["#", "Mode"], tablefmt="fancy_grid"))
    max_retries = 5
    retries = 0
    while retries < max_retries:
        try:
            choice = input("Enter your choice (1-2): ").strip()
            logger.info(f"Raw mode input received: '{choice}'")
            if choice in ["1", "2"]:
                logger.info(f"Valid execution mode selected: {choice}")
                return int(choice)
            logger.error(f"Invalid execution mode: {choice}")
            print("Invalid choice. Please enter 1 or 2.")
            retries += 1
        except EOFError:
            logger.error("EOF received during execution mode input")
            print("Input interrupted. Please enter 1 or 2.")
            retries += 1
        except KeyboardInterrupt:
            logger.info("Program interrupted by user (Ctrl+C)")
            print("\nProgram interrupted by user. Exiting.")
            sys.exit(0)
    logger.error(f"Max retries ({max_retries}) reached in display_execution_mode_menu")
    print("Too many invalid attempts. Exiting.")
    return None


def main():
    """Main function to launch network automation tasks."""
    try:
        actions_file = os.path.join(project_dir, "data/action_map.yml")
        actions = load_yaml_file(actions_file).get("actions", [])

        choice = display_menu(actions)
        if choice is None:
            logger.error("No valid action selected")
            return

        selected_action = actions[choice - 1]
        action_name = selected_action["name"]
        logger.info(f"Selected action: {action_name}")

        execution_mode = display_execution_mode_menu()
        if execution_mode is None:
            logger.error("No valid execution mode selected")
            return

        if execution_mode == 1:
            logger.info(f"Executing action {action_name} locally")
            if action_name == "code_upgrade":
                code_upgrade()
            elif action_name == "state_capture":
                state_capture.main()
            elif action_name == "config_toolbox":
                config_toolbox.main()
            elif action_name == "route_monitor":
                route_monitor.main()
            elif action_name == "bgp_toolbox":
                bgp_toolbox.main()
            else:
                network_automation_main(action_name)
        else:
            logger.info(f"Pushing action {action_name} to GitHub")
            print("GitHub push not implemented yet.")
    except Exception:
        print("Top-Level exception in launcher:")
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info("Program interrupted by user (Ctrl+C)")
        print("\nProgram interrupted by user. Exiting.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error in launcher: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
