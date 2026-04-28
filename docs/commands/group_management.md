# Group Management

## Overview

The ESP RainMaker CLI supports device grouping, allowing you to organize nodes into groups for easier management and control. Groups can be created, edited, deleted, and queried, and nodes can be added or removed from groups. Groups can also have a hierarchy (parent groups). Groups (and Matter fabrics) can also be shared with other users via the `group sharing` subcommand.

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

## Group Sharing

Groups and Matter fabrics can be shared between users. The primary user (owner) can share one or more groups with another user as either a secondary (view/control) or primary (full access) user. The receiving user accepts or declines the sharing request.

> Group sharing replaces the older node-level `sharing` command, which is deprecated. Use `group sharing` even when you want to share a single node — create a group containing that node and share the group.

All sharing operations are accessed via:

```bash
esp-rainmaker-cli group sharing <operation> [options]
```

Operations:

1. `add` — Share group(s) with a user
2. `remove` — Remove sharing with a user
3. `list` — Show sharing details for groups the current user is associated with
4. `list-requests` — List pending sharing requests (sent or received)
5. `accept` — Accept a sharing request
6. `decline` — Decline a sharing request
7. `cancel` — Cancel a pending sharing request (primary side)

### Share a group

```bash
esp-rainmaker-cli group sharing add --groups <group_id1>[,<group_id2>,...] [--user <email>] [--primary] [--sub-role <1-4>] [--metadata <json>] [--transfer] [--new-role secondary] [--raw] [--profile <profile>]
```

- `--groups`: Comma separated group ids (max 10) (required)
- `--user`: Email of the user to share with (optional)
- `--primary`: Share with primary access (default: secondary)
- `--sub-role`: Custom sub role 1-4 (optional)
- `--metadata`: Custom metadata as a JSON string (optional)
- `--transfer`: Transfer ownership of the group(s) to the user (optional)
- `--new-role`: Role to assign to self after transfer; only `secondary` is currently valid (optional, only with `--transfer`)
- `--raw`: Print the raw JSON response instead of parsed output (optional)
- `--profile`: Profile to use (optional)

If the recipient already has access to the group, the role/metadata update is applied immediately; otherwise a pending request is created and must be accepted by the recipient.

### Remove group sharing

```bash
esp-rainmaker-cli group sharing remove --groups <group_id1>[,<group_id2>,...] --user <email> [--raw] [--profile <profile>]
```

- `--groups`: Comma separated group ids (required)
- `--user`: Email of the user to unshare with (required)
- `--raw`: Print the raw JSON response instead of parsed output (optional)
- `--profile`: Profile to use (optional)

A primary user can remove any secondary user's sharing. A secondary user can pass their own email to leave the group(s).

### List sharing details

```bash
esp-rainmaker-cli group sharing list [--group-id <group_id>] [--sub-groups] [--parent-groups] [--metadata] [--raw] [--profile <profile>]
```

- `--group-id`: Fetch sharing details for a single group (optional; default: all groups associated with the user)
- `--sub-groups`: Include sharing details of sub-groups (optional)
- `--parent-groups`: Include sharing details of parent groups (optional)
- `--metadata`: Include metadata set during sharing (optional)
- `--raw`: Print the raw JSON response instead of parsed output (optional)
- `--profile`: Profile to use (optional)

### List pending requests

```bash
esp-rainmaker-cli group sharing list-requests [--id <request_id>] [--primary-user] [--raw] [--profile <profile>]
```

- `--id`: Fetch a specific request by id (optional)
- `--primary-user`: List requests raised by current user (default: requests received)
- `--raw`: Print the raw JSON response instead of parsed output (optional)
- `--profile`: Profile to use (optional)

All matching requests are returned; pagination is handled internally.

### Accept / decline / cancel a request

```bash
esp-rainmaker-cli group sharing accept  --id <request_id> [--raw] [--profile <profile>]
esp-rainmaker-cli group sharing decline --id <request_id> [--raw] [--profile <profile>]
esp-rainmaker-cli group sharing cancel  --id <request_id> [--raw] [--profile <profile>]
```

- `accept` / `decline` are used by the recipient.
- `cancel` is used by the primary user to revoke a pending request they sent.
- `--raw` on any of these prints the underlying JSON response instead of the parsed status line.

### Examples

- Share two groups with a secondary user:
  ```bash
  esp-rainmaker-cli group sharing add --groups g1,g2 --user user@example.com
  ```
- Share a group with primary access:
  ```bash
  esp-rainmaker-cli group sharing add --groups g1 --user user@example.com --primary
  ```
- Transfer ownership of a group and remain as a secondary user:
  ```bash
  esp-rainmaker-cli group sharing add --groups g1 --user newowner@example.com --transfer --new-role secondary
  ```
- List sharing details for all groups, including sub-groups and metadata:
  ```bash
  esp-rainmaker-cli group sharing list --sub-groups --metadata
  ```
- List requests received (as secondary user):
  ```bash
  esp-rainmaker-cli group sharing list-requests
  ```
- List requests raised (as primary user):
  ```bash
  esp-rainmaker-cli group sharing list-requests --primary-user
  ```
- Accept a request:
  ```bash
  esp-rainmaker-cli group sharing accept --id req123456
  ```
- Cancel a pending request:
  ```bash
  esp-rainmaker-cli group sharing cancel --id req123456
  ```
- Remove a user's access to a group:
  ```bash
  esp-rainmaker-cli group sharing remove --groups g1 --user user@example.com
  ```

### Sharing workflow

Primary user:
1. Share a group:
   ```bash
   esp-rainmaker-cli group sharing add --groups g1 --user secondary@example.com
   ```
2. Check request status:
   ```bash
   esp-rainmaker-cli group sharing list-requests --primary-user
   ```
3. Cancel if needed:
   ```bash
   esp-rainmaker-cli group sharing cancel --id <request_id>
   ```

Secondary user:
1. Check for pending requests:
   ```bash
   esp-rainmaker-cli group sharing list-requests
   ```
2. Accept a request:
   ```bash
   esp-rainmaker-cli group sharing accept --id <request_id>
   ```
3. Verify access:
   ```bash
   esp-rainmaker-cli group list
   esp-rainmaker-cli group sharing list
   ```

### Notes

- Up to 10 groups can be specified per `add` / `remove` request.
- Matter sub-groups cannot be shared individually; share the parent group instead.
- Sharing requests expire after 7 days if not accepted.
- Accepting a Matter fabric sharing request returns Matter-specific details (`fabric_id`, `root_ca`, `group_cat_id_admin`, `matter_user_id`) in the response.