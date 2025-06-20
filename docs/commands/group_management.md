# Group Management

## Overview

The ESP RainMaker CLI supports device grouping, allowing you to organize nodes into groups for easier management and control. Groups can be created, edited, deleted, and queried, and nodes can be added or removed from groups. Groups can also have a hierarchy (parent groups).

## Group Commands

### Add Group
```bash
esp-rainmaker-cli group add --name <group_name> [--description <desc>] [--mutually-exclusive] [--custom-metadata <json>] [--nodes <node1,node2>] [--type <type>] [--parent-group-id <parent_id>] [--profile <profile>]
```
- `--name`: Name of the group (required)
- `--description`: Description (optional)
- `--mutually-exclusive`: Boolean flag (optional)
- `--custom-metadata`: JSON string (optional)
- `--nodes`: Comma separated list of node IDs (optional)
- `--type`: Group type (optional)
- `--parent-group-id`: Parent group ID (optional)
- `--profile`: Profile to use (optional)

### Remove Group
```bash
esp-rainmaker-cli group remove --group-id <group_id> [--profile <profile>]
```
- `--group-id`: ID of the group to delete (required)
- `--profile`: Profile to use (optional)

### Edit Group
```bash
esp-rainmaker-cli group edit --group-id <group_id> [--name <n>] [--description <desc>] [--mutually-exclusive true|false|1|0] [--custom-metadata <json>] [--type <type>] [--parent-group-id <parent_id>] [--profile <profile>]
```
- `--group-id`: ID of the group to edit (required)
- `--name`: Name of the group (optional)
- `--description`: Description (optional)
- `--mutually-exclusive`: Set mutually exclusive flag to true/false or 1/0 (optional)
- `--custom-metadata`: JSON string (optional)
- `--type`: Group type (optional)
- `--parent-group-id`: Parent group ID (optional)
- `--profile`: Profile to use (optional)

### List Groups
```bash
esp-rainmaker-cli group list [--sub-groups] [--profile <profile>]
```
- `--sub-groups`: Include sub-groups in the output to view hierarchy (optional)
- `--profile`: Profile to use (optional)

### Show Group Details
```bash
esp-rainmaker-cli group show --group-id <group_id> [--sub-groups] [--profile <profile>]
```
- `--group-id`: ID of the group to show (required)
- `--sub-groups`: Include sub-groups in the output (optional)
- `--profile`: Profile to use (optional)

### Add Nodes to Group
```bash
esp-rainmaker-cli group add-nodes --group-id <group_id> --nodes <node1,node2> [--profile <profile>]
```
- `--group-id`: ID of the group (required)
- `--nodes`: Comma separated list of node IDs to add (required)
- `--profile`: Profile to use (optional)

### Remove Nodes from Group
```bash
esp-rainmaker-cli group remove-nodes --group-id <group_id> --nodes <node1,node2> [--profile <profile>]
```
- `--group-id`: ID of the group (required)
- `--nodes`: Comma separated list of node IDs to remove (required)
- `--profile`: Profile to use (optional)

### List Nodes in Group
```bash
esp-rainmaker-cli group list-nodes --group-id <group_id> [--node-details] [--sub-groups] [--raw] [--profile <profile>]
```
- `--group-id`: ID of the group (required)
- `--node-details`: Show detailed node info (optional)
- `--sub-groups`: Include sub-groups in the output (optional)
- `--raw`: Print raw JSON output (only with --node-details, optional)
- `--profile`: Profile to use (optional)

#### Output Details
- By default, lists node IDs in the group.
- With `--node-details`, prints detailed info for each node (same as `getnodedetails`).
- With `--raw` (only with `--node-details`), prints raw JSON response.
- With `--sub-groups`, also lists immediate sub-groups (name, ID, and description if present).

## Examples

- Create a group:
  ```bash
  esp-rainmaker-cli group add --name "Living Room" --description "All living room devices" --nodes node1,node2
  ```
- List all groups:
  ```bash
  esp-rainmaker-cli group list
  ```
- List all groups with hierarchy (showing sub-groups):
  ```bash
  esp-rainmaker-cli group list --sub-groups
  ```
- Show group details:
  ```bash
  esp-rainmaker-cli group show --group-id <group_id>
  ```
- Show group details with sub-groups:
  ```bash
  esp-rainmaker-cli group show --group-id <group_id> --sub-groups
  ```
- Add nodes to a group:
  ```bash
  esp-rainmaker-cli group add-nodes --group-id <group_id> --nodes node3,node4
  ```
- Remove nodes from a group:
  ```bash
  esp-rainmaker-cli group remove-nodes --group-id <group_id> --nodes node2
  ```
- List nodes in a group (simple):
  ```bash
  esp-rainmaker-cli group list-nodes --group-id <group_id>
  ```
- List nodes in a group with details:
  ```bash
  esp-rainmaker-cli group list-nodes --group-id <group_id> --node-details
  ```
- List nodes in a group with raw JSON details:
  ```bash
  esp-rainmaker-cli group list-nodes --group-id <group_id> --node-details --raw
  ```
- List nodes in a group and show sub-groups:
  ```bash
  esp-rainmaker-cli group list-nodes --group-id <group_id> --sub-groups
  ```
- List nodes in a group with details and sub-groups:
  ```bash
  esp-rainmaker-cli group list-nodes --group-id <group_id> --node-details --sub-groups
  ```