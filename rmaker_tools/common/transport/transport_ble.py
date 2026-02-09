# SPDX-FileCopyrightText: 2018-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
#

from . import ble_cli
from .transport import Transport


class Transport_BLE(Transport):
    def __init__(self, service_uuid, nu_lookup):
        # Store original endpoint IDs (e.g., 'ff54', 'ff55') for fallback calculation
        self.endpoint_ids = nu_lookup.copy()
        self.service_uuid = service_uuid
        self.name_uuid_lookup = None
        
        # Calculate fallback characteristic UUIDs based on service UUID
        # This is only used if auto-discovery via user descriptors fails
        # Pattern: service_uuid[:4] + endpoint_id + service_uuid[8:]
        self.fallback_lookup = {}
        for name, endpoint_id in nu_lookup.items():
            # Calculate characteristic UUID: replace bytes 4-6 with endpoint ID
            # For standard UUID '0000ffff-0000-1000-8000-00805f9b34fb' with endpoint 'ff54':
            # Result: '0000ff54-0000-1000-8000-00805f9b34fb'
            self.fallback_lookup[name] = service_uuid[:4] + endpoint_id + service_uuid[8:]

        # Get BLE client module
        self.cli = ble_cli.get_client()

    async def connect(self, devname):
        # Use client to connect to BLE device and bind to service
        # Pass endpoint names (not UUIDs) for auto-discovery via user descriptors
        if not await self.cli.connect(devname=devname, iface='hci0',
                                      chrc_names=self.endpoint_ids.keys(),
                                      fallback_srv_uuid=self.service_uuid):
            raise RuntimeError('Failed to initialize transport')

        # Primary method: Auto-discover endpoints by reading user descriptors (UUID 2901)
        # This works regardless of what UUIDs the device uses
        self.name_uuid_lookup = self.cli.get_nu_lookup()

        # Fallback: If auto-discovery failed, try calculated UUIDs
        # This handles older firmware that might not have user descriptors
        if self.name_uuid_lookup is None:
            # Try using discovered service UUID if available, otherwise use provided one
            discovered_srv_uuid = self.cli.get_service_uuid()
            actual_srv_uuid = discovered_srv_uuid if discovered_srv_uuid else self.service_uuid
            
            # Recalculate fallback UUIDs using actual service UUID
            self.name_uuid_lookup = {}
            for name, endpoint_id in self.endpoint_ids.items():
                self.name_uuid_lookup[name] = actual_srv_uuid[:4] + endpoint_id + actual_srv_uuid[8:]
            
            # Check if expected characteristics are provided by the service
            missing_endpoints = []
            for name, char_uuid in self.name_uuid_lookup.items():
                if not self.cli.has_characteristic(char_uuid):
                    missing_endpoints.append(name)
            
            if missing_endpoints:
                # Provide helpful error message
                available_chars = self.cli.get_available_characteristics()
                error_msg = f"Endpoints not found: {', '.join(missing_endpoints)}"
                error_msg += "\n\nAuto-discovery via user descriptors (UUID 2901) failed."
                error_msg += "\nFallback UUID calculation also failed."
                if available_chars:
                    error_msg += f"\n\nAvailable characteristics: {', '.join(available_chars[:10])}"
                error_msg += "\n\nPossible causes:"
                error_msg += "\n1. Endpoints not registered during NETWORK_PROV_START"
                error_msg += "\n2. Endpoints registered but missing user descriptors"
                error_msg += "\n3. Device not in provisioning mode"
                raise RuntimeError(error_msg)

    async def disconnect(self):
        await self.cli.disconnect()

    async def send_data(self, ep_name, data):
        # Write (and read) data to characteristic corresponding to the endpoint
        if ep_name not in self.name_uuid_lookup.keys():
            raise RuntimeError(f'Invalid endpoint: {ep_name}')
        return await self.cli.send_data(self.name_uuid_lookup[ep_name], data)
