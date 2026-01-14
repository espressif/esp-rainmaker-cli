# SPDX-FileCopyrightText: 2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

"""
mDNS discovery for ESP RainMaker on-network challenge-response devices
"""

import socket
import time
from typing import List, Dict, Optional, Callable

try:
    from rmaker_lib.logger import log
except ImportError:
    import logging
    log = logging.getLogger(__name__)

# Service type for discovery
MDNS_SERVICE_TYPE_CHAL_RESP = "_esp_rmaker_chal_resp._tcp.local."


class DeviceInfo:
    """Information about a discovered device"""

    def __init__(self, name: str, ip: str, port: int, properties: Dict[str, str],
                 service_type: str = "chal_resp"):
        self.name = name
        self.ip = ip
        self.port = port
        self.properties = properties
        self.service_type = service_type  # Always "chal_resp"

    @property
    def node_id(self) -> Optional[str]:
        return self.properties.get('node_id')

    @property
    def security_version(self) -> int:
        try:
            return int(self.properties.get('sec_version', '1'))
        except (ValueError, TypeError):
            return 1

    @property
    def pop_required(self) -> bool:
        return self.properties.get('pop_required', 'false').lower() == 'true'


    def __str__(self):
        return f"DeviceInfo(name={self.name}, ip={self.ip}, port={self.port}, node_id={self.node_id}, sec_ver={self.security_version}, type={self.service_type})"

    def __repr__(self):
        return self.__str__()

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'ip': self.ip,
            'port': self.port,
            'node_id': self.node_id,
            'security_version': self.security_version,
            'pop_required': self.pop_required,
            'service_type': self.service_type,
            'properties': self.properties
        }


def discover_chal_resp_devices(timeout: float = 5.0,
                               filter_func: Optional[Callable[[DeviceInfo], bool]] = None) -> List[DeviceInfo]:
    """
    Discover devices supporting challenge-response via mDNS

    Searches for _esp_rmaker_chal_resp._tcp service (used by both standalone and local control ch_resp)

    :param timeout: Discovery timeout in seconds
    :param filter_func: Optional filter function to select devices
    :return: List of discovered devices
    """
    try:
        from zeroconf import ServiceBrowser, ServiceListener, Zeroconf, IPVersion
    except ImportError:
        log.error("zeroconf library not installed. Install with: pip install zeroconf")
        raise ImportError("zeroconf library required for mDNS discovery. Install with: pip install zeroconf")

    discovered_devices: List[DeviceInfo] = []
    seen_node_ids = set()  # Track node_ids to avoid duplicates

    class ChalRespListener(ServiceListener):
        def __init__(self):
            self.devices = []

        def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            try:
                info = zc.get_service_info(type_, name)
                if info:
                    # Get IP address
                    if info.addresses:
                        ip = socket.inet_ntoa(info.addresses[0])
                    elif info.parsed_addresses():
                        ip = info.parsed_addresses()[0]
                    else:
                        log.warning(f"No IP address found for {name}")
                        return

                    # Get port
                    port = info.port

                    # Parse properties (TXT records)
                    properties = {}
                    if info.properties:
                        for key, value in info.properties.items():
                            if isinstance(key, bytes):
                                key = key.decode('utf-8', errors='ignore')
                            if isinstance(value, bytes):
                                value = value.decode('utf-8', errors='ignore')
                            properties[key] = value

                    # All challenge-response devices use _esp_rmaker_chal_resp._tcp
                    service_type = "chal_resp"

                    # Extract instance name (before the service type)
                    instance_name = name.replace(f".{type_}", "")

                    device = DeviceInfo(
                        name=instance_name,
                        ip=ip,
                        port=port,
                        properties=properties,
                        service_type=service_type
                    )

                    log.info(f"Discovered device: {device}")
                    self.devices.append(device)

            except Exception as e:
                log.debug(f"Error processing service {name}: {e}")

        def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            pass

        def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            pass

    log.info(f"Discovering devices via mDNS (timeout: {timeout}s)...")

    try:
        zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        listener = ChalRespListener()

        # Browse for challenge-response service
        browser = ServiceBrowser(zeroconf, MDNS_SERVICE_TYPE_CHAL_RESP, listener)

        # Wait for discovery
        time.sleep(timeout)

        # Collect discovered devices
        discovered_devices = listener.devices

        # Clean up
        browser.cancel()
        zeroconf.close()

    except Exception as e:
        log.error(f"mDNS discovery failed: {e}")
        raise

    # Remove duplicates (same node_id)
    unique_devices = []
    for device in discovered_devices:
        node_id = device.node_id
        if node_id:
            if node_id not in seen_node_ids:
                seen_node_ids.add(node_id)
                unique_devices.append(device)
        else:
            unique_devices.append(device)
    discovered_devices = unique_devices

    # Apply filter if provided
    if filter_func:
        discovered_devices = [d for d in discovered_devices if filter_func(d)]

    log.info(f"Discovery complete. Found {len(discovered_devices)} device(s)")
    return discovered_devices


def discover_device_by_name(device_name: str, timeout: float = 5.0) -> Optional[DeviceInfo]:
    """
    Discover a specific device by name

    :param device_name: Device name or node_id to search for
    :param timeout: Discovery timeout in seconds
    :return: DeviceInfo if found, None otherwise
    """
    def name_filter(device: DeviceInfo) -> bool:
        # Match by instance name or node_id
        return (device.name.lower() == device_name.lower() or
                (device.node_id and device.node_id.lower() == device_name.lower()))

    devices = discover_chal_resp_devices(timeout=timeout, filter_func=name_filter)

    if devices:
        return devices[0]
    return None


def discover_device_by_ip(ip: str, port: int = 80) -> DeviceInfo:
    """
    Create a DeviceInfo for a device with known IP (bypasses mDNS discovery)

    :param ip: Device IP address
    :param port: HTTP server port
    :return: DeviceInfo with unknown properties
    """
    return DeviceInfo(
        name=ip,
        ip=ip,
        port=port,
        properties={}
    )


def list_discovered_devices(devices: List[DeviceInfo]) -> None:
    """
    Print a formatted list of discovered devices

    :param devices: List of discovered devices
    """
    if not devices:
        print("No devices discovered.")
        return

    print(f"\nDiscovered {len(devices)} device(s):")
    print("-" * 120)
    print(f"{'#':<3} {'Instance Name':<20} {'Node ID':<25} {'IP Address':<16} {'Port':<6} {'Sec':<4} {'PoP':<8} {'Service':<12}")
    print("-" * 120)

    for i, device in enumerate(devices, 1):
        instance_name = device.name or "Unknown"
        if len(instance_name) > 19:
            instance_name = instance_name[:16] + "..."

        node_id = device.node_id or "Unknown"
        if len(node_id) > 24:
            node_id = node_id[:21] + "..."

        # Show PoP requirement status
        if device.security_version == 1:
            pop_status = "Yes" if device.pop_required else "No"
        elif device.security_version == 2:
            pop_status = "SRP6a"
        else:
            pop_status = "N/A"

        print(f"{i:<3} {instance_name:<20} {node_id:<25} {device.ip:<16} {device.port:<6} {device.security_version:<4} {pop_status:<8} {'ChalResp':<12}")

    print("-" * 120)


def select_device_interactive(devices: List[DeviceInfo]) -> Optional[DeviceInfo]:
    """
    Interactively select a device from the list

    :param devices: List of discovered devices
    :return: Selected device or None if cancelled
    """
    if not devices:
        return None

    list_discovered_devices(devices)

    if len(devices) == 1:
        # Single device - ask for confirmation
        try:
            choice = input("\nProceed with this device? (y/n): ").strip().lower()
            if choice in ('y', 'yes', ''):
                return devices[0]
            else:
                return None
        except KeyboardInterrupt:
            return None

    # Multiple devices - ask for selection
    while True:
        try:
            choice = input("\nSelect device number (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                return None

            index = int(choice) - 1
            if 0 <= index < len(devices):
                return devices[index]
            else:
                print(f"Invalid selection. Please enter a number between 1 and {len(devices)}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            return None

