import os
import logging
import datetime
from typing import List
import git
from scripts.utils import load_yaml_file

logger = logging.getLogger(__name__)


def git_commit_and_push(
    repo_path: str, action_name: str, files_to_commit: List[str]
) -> bool:
    """Add, commit, and push specified files to the Git repository."""
    logger.info(f"Starting git_commit_and_push for action: {action_name}")

    # Load git configuration
    git_config_file = os.path.join(repo_path, "data/git_config.yml")
    try:
        git_config = load_yaml_file(git_config_file)
    except Exception as e:
        logger.error(f"Failed to load git_config.yml: {e}")
        print(f"Failed to load git_config.yml: {e}")
        return False

    repo_url = git_config["git"]["repository_url"]
    branch = git_config["git"]["branch"]
    username = git_config["git"]["username"]
    token = git_config["git"]["token"]

    # Replace token placeholder with environment variable if present
    if token == "{{ GIT_TOKEN }}":
        token = os.getenv("GIT_TOKEN")
        if not token:
            token = input("Enter GitHub personal access token: ")
            if not token:
                logger.error("No GitHub token provided")
                print("No GitHub token provided")
                return False

    # Construct authenticated repo URL
    if repo_url.startswith("https://"):
        auth_repo_url = repo_url.replace("https://", f"https://{username}:{token}@")
    else:
        logger.error(f"Unsupported repository URL scheme: {repo_url}")
        print(f"Unsupported repository URL scheme: {repo_url}")
        return False

    try:
        # Initialize repository
        repo = git.Repo(repo_path)
        logger.info(f"Initialized repository at {repo_path}")

        # Add files to commit
        for file_path in files_to_commit:
            if os.path.exists(os.path.join(repo_path, file_path)):
                repo.git.add(file_path)
                logger.info(f"Added file: {file_path}")
            else:
                logger.warning(f"File not found: {file_path}")
                print(f"File not found: {file_path}")

        # Check if there are changes to commit
        if repo.is_dirty():
            # Commit changes
            commit_message = f"Update for action '{action_name}' at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            repo.index.commit(commit_message)
            logger.info(f"Committed changes: {commit_message}")

            # Push to remote
            origin = repo.remote(name="origin")
            origin.set_url(auth_repo_url)  # Set authenticated URL
            origin.push(refspec=f"HEAD:{branch}")
            logger.info(f"Pushed to {repo_url} branch {branch}")
            print(f"Successfully pushed to {repo_url} branch {branch}")
            return True
        else:
            logger.info("No changes to commit")
            print("No changes to commit")
            return True

    except Exception as e:
        logger.error(f"Git operation failed: {e}")
        print(f"Git operation failed: {e}")
        return False


if __name__ == "__main__":
    # Example usage for testing
    repo_path = "/home/nikos/github/ngeran/vector-py"
    action_name = "test_action"
    files_to_commit = [
        "scripts/launcher.py",
        "scripts/network_automation.py",
        "scripts/connect_to_hosts.py",
        "scripts/actions.py",
        "scripts/interface_actions.py",
        "scripts/diagnostic_actions.py",
        "scripts/route_monitor.py",
        "scripts/utils.py",
        "scripts/main.py",
        "scripts/junos_actions.py",
        "data/hosts_data.yml",
        "data/actions.yml",
        "data/action_map.yml",
        "data/inventory.yml",
        "data/git_config.yml",
        "templates/interface_template.j2",
    ]
    git_commit_and_push(repo_path, action_name, files_to_commit)
