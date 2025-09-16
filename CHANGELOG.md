# Changelog

All major changes to ESP RainMaker CLI will be documented in this file.

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
