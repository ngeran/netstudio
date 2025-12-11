import os
import logging
import subprocess
from datetime import datetime
from typing import List, Tuple

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            "/home/nikos/github/ngeran/vector-py/network_automation.log"
        ),
        logging.StreamHandler(),
    ],
)


def check_junos_eznc_version() -> Tuple[bool, str]:
    """Check if junos-eznc is installed and at least version 2.6.0."""
    try:
        result = subprocess.run(
            ["pip", "show", "junos-eznc"], capture_output=True, text=True, check=True
        )
        version_line = [
            line for line in result.stdout.split("\n") if line.startswith("Version:")
        ]
        if not version_line:
            return False, "junos-eznc not found. Install with: pip install junos-eznc"
        version = version_line[0].split(": ")[1].strip()
        major, minor, _ = map(int, version.split("."))
        if major < 2 or (major == 2 and minor < 6):
            return (
                False,
                f"junos-eznc version {version} is too old. Upgrade with: pip install --upgrade junos-eznc",
            )
        return True, f"junos-eznc version {version} is compatible"
    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking junos-eznc: {e}")
        return False, f"Error checking junos-eznc: {e}"
    except Exception as e:
        logger.error(f"Unexpected error checking junos-eznc: {e}")
        return False, f"Unexpected error checking junos-eznc: {e}"


def verify_code_upgrade_script() -> Tuple[bool, str]:
    """Verify code_upgrade.py exists and has the expected image check function."""
    script_path = "/home/nikos/github/ngeran/vector-py/scripts/code_upgrade.py"
    try:
        if not os.path.exists(script_path):
            return False, f"code_upgrade.py not found at {script_path}"
        with open(script_path, "r") as f:
            content = f.read()
            if "def check_image_exists" not in content:
                return (
                    False,
                    f"code_upgrade.py at {script_path} is outdated (missing check_image_exists)",
                )
        return True, f"code_upgrade.py verified at {script_path}"
    except Exception as e:
        logger.error(f"Error verifying code_upgrade.py: {e}")
        return False, f"Error verifying code_upgrade.py: {e}"


def clear_python_cache() -> List[str]:
    """Generate commands to clear Python cache."""
    return [
        "find /home/nikos/github/ngeran/vector-py -name '*.pyc' -delete",
        "rm -rf /home/nikos/github/ngeran/vector-py/scripts/__pycache__",
        "rm -rf /home/nikos/github/ngeran/vector-py/network-automation-launcher/__pycache__",
        "echo 'Python cache cleared'",
    ]


def stabilize_srx320() -> List[Tuple[str, str]]:
    """Generate steps to stabilize SRX320."""
    return [
        ("ssh admin@172.27.200.200", "Connect to SRX320"),
        ("show system alarms", "Check for active alarms"),
        ("show system storage", "Verify /cf/var has ~3.2G available"),
        (
            'show system processes extensive | match "PID|%CPU|%MEM"',
            "Check CPU/memory usage (<80% ideal)",
        ),
        ("start shell user root", "Enter root shell"),
        ("ls -lh /var/run/pkg.active", "Check for package lock file"),
        (
            "rm -f /var/run/pkg.active",
            "Remove lock file if it exists (run only if file is present)",
        ),
        ("exit", "Exit root shell"),
        ("request system reboot", "Reboot SRX320 to clear resource exhaustion"),
        ("echo 'Wait 5-10 minutes, then reconnect'", "Reminder to wait for reboot"),
        ("ssh admin@172.27.200.200", "Reconnect to SRX320"),
        ("show version", "Confirm version is 24.2R1-S2.5 or 23.4R2-S3.9"),
        ("show system processes | match package", "Ensure no active install processes"),
        ("show system alarms", "Verify no new alarms"),
        ("show system storage", "Confirm ~3.2G available on /cf/var"),
        ("start shell user root", "Enter root shell"),
        ("ls -lh /var/run/pkg.active", "Confirm no package lock file"),
        ("df -k /cf/var", "Verify filesystem space"),
        ("exit", "Exit root shell"),
        (
            "request system software validate /var/tmp/junos-srxsme-23.4R2-S3.9.tgz",
            "Validate image (may take 15+ minutes)",
        ),
    ]


def cleanup_srx210h() -> List[Tuple[str, str]]:
    """Generate steps to clean up SRX210H filesystem."""
    return [
        ("ssh admin@172.27.200.201", "Connect to SRX210H"),
        ("request system storage cleanup", "Run automatic cleanup"),
        ("start shell user root", "Enter root shell"),
        ("du -sk /cf/var/* | sort -nr", "Identify space usage in /cf/var"),
        ("ls -lh /cf/var/tmp /cf/var/log", "List files in /cf/var/tmp and /cf/var/log"),
        ("rm -rf /cf/var/log/*.gz", "Remove compressed logs"),
        (
            "rm -rf /cf/var/tmp/*.tgz",
            "Remove old images (keep junos-srxsme-12.1X46-D86-domestic.tgz)",
        ),
        (
            'find /cf/var/log -type f -name "*.log" -exec rm -f {} \\;',
            "Remove remaining logs",
        ),
        ("df -k /cf/var /config", "Verify >100 MB free on /cf/var"),
        ("ls -lh /cf/var/tmp", "Confirm junos-srxsme-12.1X46-D86-domestic.tgz exists"),
        (
            "file checksum md5 /var/tmp/junos-srxsme-12.1X46-D86-domestic.tgz",
            "Verify image integrity",
        ),
        ("exit", "Exit root shell"),
    ]


def generate_manual_fallback() -> List[Tuple[str, str]]:
    """Generate manual fallback commands for both devices."""
    return [
        ("echo 'SRX320 Manual Downgrade'", "Header for SRX320 fallback"),
        ("ssh admin@172.27.200.200", "Connect to SRX320"),
        (
            "request system software add /var/tmp/junos-srxsme-23.4R2-S3.9.tgz no-validate reboot",
            "Manual downgrade with reboot",
        ),
        ("echo 'Wait 5-10 minutes, then verify'", "Reminder to wait for reboot"),
        ("ssh admin@172.27.200.200", "Reconnect to SRX320"),
        ("show version", "Confirm version is 23.4R2-S3.9"),
        ("echo 'SRX210H Manual Upgrade'", "Header for SRX210H fallback"),
        ("ssh admin@172.27.200.201", "Connect to SRX210H"),
        (
            "request system software add /var/tmp/junos-srxsme-12.1X46-D86-domestic.tgz no-validate reboot",
            "Manual upgrade with reboot",
        ),
        (
            "echo 'If SRX210H lacks space, move image to /mfs'",
            "Note for SRX210H space issue",
        ),
        ("start shell user root", "Enter root shell on SRX210H"),
        (
            "mv /cf/var/tmp/junos-srxsme-12.1X46-D86-domestic.tgz /mfs/",
            "Move image to /mfs",
        ),
        ("exit", "Exit root shell"),
        (
            "request system software add /mfs/junos-srxsme-12.1X46-D86-domestic.tgz no-validate reboot",
            "Manual upgrade from /mfs",
        ),
    ]


def cleanup_srx320_post_downgrade() -> List[Tuple[str, str]]:
    """Generate steps to clean up SRX320 after downgrade."""
    return [
        ("ssh admin@172.27.200.200", "Connect to SRX320"),
        ("start shell user root", "Enter root shell"),
        ("rm -f /cf/var/tmp/junos-srxsme-24.2R1-S2.5.tgz", "Remove old image"),
        ("df -k /cf/var", "Verify filesystem space"),
        ("exit", "Exit root shell"),
        ("request system storage cleanup", "Run automatic cleanup"),
        ("start shell user root", "Enter root shell"),
        ("ls -lh /cf/var/tmp", "List remaining files in /cf/var/tmp"),
        ("df -k /cf/var", "Confirm filesystem space"),
        ("exit", "Exit root shell"),
    ]


def capture_upgrade_steps() -> None:
    """Generate and save all upgrade preparation steps."""
    logger.info("Generating upgrade preparation steps")
    print("Generating upgrade preparation steps...")

    steps: List[Tuple[str, str, str]] = []

    # Section 1: Prerequisites
    steps.append(("Prerequisites", "", ""))
    junos_ok, junos_msg = check_junos_eznc_version()
    steps.append(("", junos_msg, "Check junos-eznc version"))
    if not junos_ok:
        steps.append(
            ("", "pip install --upgrade junos-eznc", "Upgrade junos-eznc if needed")
        )

    script_ok, script_msg = verify_code_upgrade_script()
    steps.append(("", script_msg, "Verify code_upgrade.py"))
    if not script_ok:
        steps.append(
            (
                "",
                "echo 'Ensure code_upgrade.py is updated with artifact ID 24b56648-b4e1-485c-ae2d-c4e3de3c60cc'",
                "Update script if outdated",
            )
        )

    steps.append(
        ("", "cd /home/nikos/github/ngeran/vector-py", "Navigate to project directory")
    )
    for cmd in clear_python_cache():
        steps.append(("", cmd, "Clear Python cache"))

    # Section 2: SRX320 Stabilization
    steps.append(("SRX320 Stabilization (172.27.200.200)", "", ""))
    for cmd, desc in stabilize_srx320():
        steps.append(("", cmd, desc))

    # Section 3: SRX210H Cleanup
    steps.append(("SRX210H Cleanup (172.27.200.201)", "", ""))
    for cmd, desc in cleanup_srx210h():
        steps.append(("", cmd, desc))

    # Section 4: Run Upgrade Script
    steps.append(("Run Upgrade Script", "", ""))
    steps.append(
        ("", "cd /home/nikos/github/ngeran/vector-py", "Navigate to project directory")
    )
    steps.append(
        ("", "python network-automation-launcher/launcher.py", "Run launcher.py")
    )
    steps.append(
        (
            "",
            "echo 'Input for SRX320: Choice 4, Mode 1, Vendor 1, Product 3, Release 1, Host 172.27.200.200, Username admin, Password manolis1'",
            "Note SRX320 inputs",
        )
    )
    steps.append(
        (
            "",
            "echo 'Input for SRX210H: Choice 4, Mode 1, Vendor 1, Product 4, Release 1, Host 172.27.200.201, Username admin, Password manolis1'",
            "Note SRX210H inputs",
        )
    )

    # Section 5: Manual Fallback
    steps.append(("Manual Fallback (if script fails)", "", ""))
    for cmd, desc in generate_manual_fallback():
        steps.append(("", cmd, desc))

    # Section 6: SRX320 Post-Downgrade Cleanup
    steps.append(("SRX320 Post-Downgrade Cleanup", "", ""))
    for cmd, desc in cleanup_srx320_post_downgrade():
        steps.append(("", cmd, desc))

    # Format and save output
    output_file = "/home/nikos/github/ngeran/vector-py/upgrade_steps.txt"
    try:
        with open(output_file, "w") as f:
            f.write(
                f"Upgrade Preparation Steps - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            f.write("=" * 80 + "\n\n")
            current_section = ""
            for section, cmd, desc in steps:
                if section:
                    current_section = section
                    f.write(f"{current_section}\n")
                    f.write("-" * len(current_section) + "\n\n")
                if cmd and desc:
                    f.write(f"Command: {cmd}\n")
                    f.write(f"Description: {desc}\n\n")
                elif cmd:
                    f.write(f"Command: {cmd}\n\n")
        logger.info(f"Steps saved to {output_file}")
        print(f"Steps saved to {output_file}")

        # Print to console
        print("\nUpgrade Preparation Steps:")
        print("=" * 80 + "\n")
        current_section = ""
        for section, cmd, desc in steps:
            if section and section != current_section:
                current_section = section
                print(f"{current_section}")
                print("-" * len(current_section) + "\n")
            if cmd and desc:
                print(f"Command: {cmd}")
                print(f"Description: {desc}\n")
            elif cmd:
                print(f"Command: {cmd}\n")
    except Exception as e:
        logger.error(f"Error saving steps to {output_file}: {e}")
        print(f"Error saving steps to {output_file}: {e}")


if __name__ == "__main__":
    try:
        capture_upgrade_steps()
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        print("\nScript interrupted by user. Exiting.")
    except Exception as e:
        logger.error(f"Error in capture_upgrade_steps: {e}")
        print(f"Error: {e}")
