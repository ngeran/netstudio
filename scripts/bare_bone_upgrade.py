import time

from jnpr.junos import Device
from jnpr.junos.exception import ConnectError, ConnectRefusedError, RpcError
from jnpr.junos.utils.sw import SW

# Device credentials and image path
device_ip = "172.27.200.200"
username = "admin"
password = "manolis1"
# image_path = "/var/tmp/junos-srxsme-23.4R2-S3.9.tgz"
image_path = "/var/tmp/junos-srxsme-24.2R1-S2.5.tgz"

# Max retries for reconnection after reboot
MAX_RETRIES = 30
RETRY_DELAY = 30  # seconds between retries

# Target version for comparison
TARGET_VERSION = "23.4R2-S3.9"


def get_junos_version(dev):
    # Get the device facts, including the version
    facts = dev.facts
    return facts.get("version", "Unknown version")


def reconnect_device():
    # Try to reconnect up to MAX_RETRIES times
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            print(
                f"Attempting to reconnect to {device_ip} (Attempt {retry_count + 1}/{MAX_RETRIES})..."
            )
            dev = Device(host=device_ip, user=username, passwd=password)
            dev.open()
            print(f"✅ Successfully logged in to {device_ip} after reboot.")
            return dev
        except ConnectRefusedError:
            print(
                f"❌ Connection refused. Device not reachable yet. Retrying in {RETRY_DELAY} seconds..."
            )
            time.sleep(RETRY_DELAY)
            retry_count += 1
        except ConnectError as e:
            print(f"❌ Connection error: {e}")
            break
    return None  # Return None if connection fails after retries


try:
    print("Connecting to device...")
    dev = Device(host=device_ip, user=username, passwd=password)
    dev.open()

    print(f"✅ Successfully logged in to {device_ip}")

    sw = SW(dev)

    print("Installing software with validation (no reboot)...")
    success = sw.install(package=image_path, validate=True, no_copy=True, progress=True)

    if success:
        print("✅ Installation validated successfully. Rebooting...")
        sw.reboot()

        # Wait for device to come back online (reconnect with retry mechanism)
        dev = reconnect_device()

        if dev:
            # Get and print the new version after the reboot
            new_version = get_junos_version(dev)
            print(f"✅ Device is back online. Current JUNOS version: {new_version}")

            # Check if the version matches the target version and print a final message
            if new_version == TARGET_VERSION:
                print(f"✅ The device has been successfully upgraded to {new_version}.")
            else:
                print(
                    f"❌ Version mismatch: Target version was {TARGET_VERSION}, but the current version is {new_version}."
                )
        else:
            print("❌ Device could not be reached after multiple attempts. Exiting...")

    else:
        print("❌ Installation did not complete successfully. No reboot issued.")

    dev.close()

except RpcError as e:
    print(f"❌ RPC error during install: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
