# ESP RainMaker CLI Documentation

This directory contains detailed documentation and examples for the ESP RainMaker CLI tool.

## Overview

The ESP RainMaker CLI (Command Line Interface) provides a set of commands to interact with the ESP RainMaker cloud service. It allows you to manage nodes, control devices, set parameters, manage schedules, handle node sharing, and perform other operations related to your ESP RainMaker devices.

## Installation

### Global Installation
```bash
pip install esp-rainmaker-cli
```

### Using a Virtual Environment (recommended)
```bash
# Create a virtual environment
python3 -m venv rainmaker-env

# Activate the virtual environment
# On macOS/Linux:
source rainmaker-env/bin/activate
# On Windows:
# rainmaker-env\Scripts\activate

# Install ESP RainMaker CLI
pip install esp-rainmaker-cli

# When finished, you can deactivate the virtual environment
deactivate
```

## Available Commands

The CLI supports the following main commands:

### Configuration and Profile Management

* `configure --region <region>` - Configure ESP RainMaker region (china, global)
* `profile list` - List all available profiles
* `profile current` - Show current profile information
* `profile switch <name>` - Switch to a different profile
* `profile add <name> --base-url <url>` - Add a new custom profile
* `profile remove <name>` - Remove a custom profile

### User Management

* `login` - Log in to the ESP RainMaker service
* `logout` - Log out from the ESP RainMaker service
* `signup` - Sign up for a new ESP RainMaker account
* `forgotpassword` - Reset a forgotten password
* `getuserinfo` - Get details of the currently logged-in user

### Node Management

* `getnodes` - List all nodes associated with the user
* `getnodeconfig` - Get node configuration
* `getnodestatus` - Get online/offline status of the node
* `getnodedetails` - Get detailed information for all nodes or a specific node
* `removenode` - Remove user node mapping
* `node add-tags` - Add tags to a node
* `node remove-tags` - Remove tags from a node
* `node set-metadata` - Set or update metadata for a node
* `node delete-metadata` - Delete metadata from a node

### Parameter Management

* `getparams` - Get node parameters
* `setparams` - Set node parameters

### Schedule Management

* `getschedules` - Get schedule information for a specific node
* `setschedule` - Manage schedules for a specific node (add/edit/remove/enable/disable)
  * [Detailed Schedule Examples](./commands/scheduling.md)

### Node Sharing

* `sharing add_user` - Request to add user for sharing nodes
* `sharing remove_user` - Remove user from shared nodes
* `sharing accept` - Accept sharing request
* `sharing decline` - Decline sharing request
* `sharing cancel` - Cancel sharing request
* `sharing list_nodes` - List nodes sharing details
* `sharing list_requests` - List pending requests

### Command Response (Beta)

* `create_cmd_request` - Create a command response request for nodes
* `get_cmd_requests` - Get command response requests details

### Device Setup

* `claim` - Claim the node connected to a serial port (get cloud credentials)
* `provision` - Provision the node to join Wi-Fi network

### Other Operations

* `getmqtthost` - Get the MQTT Host URL to be used in the firmware
* `raw-api` - Make authenticated raw API calls to RainMaker backend for testing/debugging

## Detailed Documentation

For detailed documentation on specific commands, refer to the following files:

* [Profile Management](./commands/profile_management.md)
* [Schedule Management](./commands/scheduling.md)
* [Node Sharing](./commands/node_sharing.md)
* [Parameter Management](./commands/parameters.md)
* [Node Management](./commands/node_management.md)
* [Node Tags and Metadata](./commands/node_tags_metadata.md)
* [Claiming](./commands/claiming.md)
* [Provisioning](./commands/provisioning.md)
* [Command Response](./commands/command_response.md)
* [ESP Local Control](./commands/local_control.md)
* [Raw API](./commands/raw_api.md)

## Examples

Each command documentation includes practical examples of usage.

## Getting Help

You can get help on any command by running:

```bash
esp-rainmaker-cli <command> --help
```

For the full list of available commands:

```bash
esp-rainmaker-cli --help
```
