# Changelog

All major changes to ESP RainMaker CLI will be documented in this file.

## [1.10.0] - 22-Jan-2026
### Added
- BLE local control support for `getparams`, `setparams`, and `getnodeconfig` commands during provisioning phase:
  - `--local-raw` option to use custom provisioning endpoints for direct parameter/config access over BLE
  - `--device-name` option to specify the device name for BLE discovery
  - Fragmented transfer support for `getnodeconfig` to handle BLE MTU limits
- `--proxy-report` option for proxy reporting to cloud backend (if the node is already mapped to the user):
  - Sends timestamp to node and receives signed response (parameters/config + timestamp + signature)
  - Reports to cloud on behalf of the node

## [1.9.1] - 21-Jan-2026
### Bugfixes
- The IPv6 address is not supported for on-network challenge-response.

## [1.9.0] - 14-Jan-2026
### Added
- Support for on-network user-node mapping via the "provision" command for scenarios wherein the RainMaker node is already
  connected to the network via some mechanism independent of RainMaker provisioning.

## [1.8.2] - 08-Jan-2026
### Added
- An option --no-wifi to 'provision' command to allow challenge-response based user-node mapping without Wi-Fi provisioning.
- A new command `raw-api` which will allow invoking any user API supported by ESP RainMaker.

### Bugfixes
- The reset provisioning command sent for retrying on failure did not have complete command data.

## [1.8.1] - 19-Dec-2025
### Added
- An option --no-retry for provisioning, to avoid user-interactive prompts asking to retry in case of failures

## [1.8.0] - 18-Dec-2025
### Added
- Retry support for WiFi provisioning - allows users to retry provisioning on failure,
  resets device state machine using prov-ctrl endpoint, and sends new credentials on the same secure session
- Support for passing QR code payload to provisioning command

## [1.7.0] - 11-Nov-2025
### Added
- BLE Transport support for provisioning
- Challenge-response based user-node mapping
- Local control over HTTP
- Security v2 for provisioning and local control

## [1.6.0] - 16-Sep-2025
### Added
- Support for camera device type in claiming

## [1.5.4] - 16-Sep-2025
### Added
- Support for changing logs path
- Support for passing access token externally

## [1.5.3] - 26-Jun-2025
### Added
 - New `deleteuser` command for permanent account deletion with two-step verification
### Fixed
 - login command was not displaying currently logged-in user when session exists
 - login, signup, forgotpassword commands were giving deprecation warning for pkg_resources

## [1.5.2] - 23-Jun-2025
### Fixed
- `requirement`: bump esp-idf-nvs-partition-gen to v0.1.9

## [1.5.1] - 20-Jun-2025
### Fixed
- `claim` command was failing

## [1.5.0] - 18-Jun-2025
### Added
- Group management support with the following subcommands:
  - `add`: Create a new group with optional description, type, and parent group
  - `remove`: Delete an existing group
  - `edit`: Modify group properties including name, description, and parent
  - `list`: Display all available groups
  - `show`: View detailed information about a specific group
  - `add-nodes`: Add one or more nodes to a group
  - `remove-nodes`: Remove nodes from a group
  - `list-nodes`: View nodes in a group with optional detailed info and sub-groups

## [1.4.0] - 16-Jun-2025
### Added
- Support for setting parameters and schedules for multiple nodes in a single command
- New module `rmaker_lib/schedule_utils.py` for schedule formatting and parsing

## [1.3.0] - 16-Jun-2025
### Added
- Multi-profile support for managing multiple ESP RainMaker deployments
- New `profile` command with subcommands:
  - `list`: Show all configured profiles
  - `current`: Display active profile
  - `switch`: Change to a different profile
  - `add`: Configure a new profile
  - `remove`: Delete an existing profile
- Global `--profile` option available with all commands to specify which profile to use

## [1.2.0] - 06-Jun-2025
### Added
- New `getnodedetails` command for formatted node information with raw data option
- Support for schedule management with `get/setschedule` commands
- Comprehensive documentation for all supported features
