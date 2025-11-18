# ESP RainMaker Provisioning Module

This module provides enhanced device provisioning capabilities for ESP RainMaker, supporting the latest ESP-IDF provisioning features.

## Features

### Transport Modes
- **BLE (Bluetooth Low Energy)**: Direct device communication via Bluetooth
- **SoftAP (Wi-Fi Access Point)**: Device creates Wi-Fi hotspot for provisioning
- **Console (Serial/UART)**: Serial port communication

### Security Schemes
- **Security 0**: No encryption (for testing only)
- **Security 1**: X25519 key exchange + AES-CTR + Proof of Possession
- **Security 2**: SRP6a authentication + AES-GCM encryption

### Key Capabilities
- Auto-detection of security schemes
- Async/sync compatibility for BLE transport
- ESP RainMaker user association
- Wi-Fi network scanning and configuration
- Error handling and recovery

## Updated Components

### Proto Files Structure
```
protocomm/
├── proto/              # Protocol buffer definitions
│   ├── constants.proto
│   ├── sec0.proto
│   ├── sec1.proto
│   ├── sec2.proto      # Added: Security 2 support
│   └── session.proto
└── python/             # Generated Python modules
    ├── constants_pb2.py
    ├── sec0_pb2.py
    ├── sec1_pb2.py
    ├── sec2_pb2.py     # Added: Security 2 support
    └── session_pb2.py

wifi_provisioning/
├── proto/
│   ├── wifi_config.proto
│   ├── wifi_constants.proto
│   └── wifi_scan.proto
└── python/
    ├── wifi_config_pb2.py
    ├── wifi_constants_pb2.py
    └── wifi_scan_pb2.py

config/                 # ESP RainMaker specific protocols
├── custom_cloud_config.proto          # Legacy user mapping
├── esp_rmaker_user_mapping.proto      # Updated user mapping
├── esp_rmaker_claim.proto              # Device claiming
├── esp_rmaker_chal_resp.proto          # Challenge-response auth
└── python/             # Generated modules
    ├── custom_cloud_config_pb2.py
    ├── esp_rmaker_user_mapping_pb2.py
    ├── esp_rmaker_claim_pb2.py
    └── esp_rmaker_chal_resp_pb2.py
```

### Enhanced Modules
- **Security 2**: Added SRP6a authentication with username/password
- **BLE Transport**: Async/sync compatibility wrapper for ESP-IDF transport
- **User Mapping**: Updated to use latest ESP RainMaker protocols
- **Utils**: Enhanced convenience functions for data conversion

## Usage Examples

### Basic Provisioning
```python
from rmaker_tools.rmaker_prov.esp_rainmaker_prov import provision_device

# BLE provisioning with auto-detection
provision_device(
    transport_mode='ble',
    pop='abcd1234',
    userid='user@example.com',
    secretkey='secret123',
    device_name='PROV_d76c30'
)
```

### Advanced Security
```python
# Security 2 (SRP6a) provisioning
provision_device(
    transport_mode='softap',
    pop='abcd1234',
    userid='user@example.com',
    secretkey='secret123',
    security_version=2,
    sec2_username='admin',
    sec2_password='secure123'
)
```

## Dependencies

### Required Packages
- `bleak>=0.20.0` - For BLE communication
- `protobuf>=3.20.0` - Protocol buffer support
- `cryptography` - Cryptographic operations
- `future` - Python 2/3 compatibility

### Installation
```bash
pip install bleak>=0.20.0 protobuf>=3.20.0
```

## Compatibility

### ESP-IDF Integration
This module maintains compatibility with:
- ESP-IDF v5.0+ provisioning protocols
- ESP RainMaker firmware v1.0+
- Legacy ESP RainMaker CLI commands

### Backward Compatibility
- Supports both old and new protocol buffer definitions
- Fallback mechanisms for missing modules
- Compatible with existing ESP RainMaker workflows

## Source Information

### Proto Files Origins
- **ESP-IDF Components**: Latest protocomm and wifi_provisioning
- **ESP RainMaker**: Core ESP RainMaker protocol definitions
- **IDF-Extra-Components**: Network provisioning enhancements

### Last Updated
- ESP-IDF protocols: Latest master branch
- ESP RainMaker protocols: Latest core definitions
- Security enhancements: SRP6a implementation from ESP-IDF v5.0+

## Development

### Regenerating Proto Files
```bash
# Regenerate Python modules from .proto files
cd config/
protoc --python_out=. *.proto
```

### Testing
```bash
# Test BLE provisioning
python -c "
from esp_rainmaker_prov import provision_device
provision_device('ble', 'test1234', 'user@test.com', 'secret', device_name='PROV_test')
"
```