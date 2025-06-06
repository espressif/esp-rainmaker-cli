# Node Sharing Documentation

ESP RainMaker supports sharing nodes between users. This allows a primary user to share their nodes with secondary users, enabling them to control and monitor the devices.

## Overview

Node sharing in ESP RainMaker involves three main entities:
- **Primary User**: The user who owns the node and initiates sharing
- **Secondary User**: The user who receives access to the shared node
- **Sharing Request**: A request sent from the primary user to the secondary user

## Commands

All node sharing commands are accessed through the `sharing` subcommand:

```bash
esp-rainmaker-cli sharing <operation> [options]
```

### Available Operations

1. **add_user**: Request to add a user for sharing nodes
2. **remove_user**: Remove a user from shared nodes
3. **accept**: Accept a sharing request
4. **decline**: Decline a sharing request
5. **cancel**: Cancel a pending sharing request
6. **list_nodes**: List nodes sharing details
7. **list_requests**: List pending sharing requests

## Detailed Command Usage

### Adding a User to Share Nodes

As a primary user, you can share your nodes with another user:

```bash
esp-rainmaker-cli sharing add_user --user <email> --nodes <nodeid1>,<nodeid2>,...
```

Example:
```bash
esp-rainmaker-cli sharing add_user --user secondary@example.com --nodes abcd1234,efgh5678
```

This sends a sharing request to the specified user's email. The request will expire in 7 days if not accepted.

### Removing a User from Shared Nodes

As a primary user, you can remove a secondary user's access to your nodes:

```bash
esp-rainmaker-cli sharing remove_user --user <email> --nodes <nodeid1>,<nodeid2>,...
```

Example:
```bash
esp-rainmaker-cli sharing remove_user --user secondary@example.com --nodes abcd1234,efgh5678
```

### Accepting a Sharing Request

As a secondary user, you can accept a sharing request sent to you:

```bash
esp-rainmaker-cli sharing accept --id <request_id>
```

Example:
```bash
esp-rainmaker-cli sharing accept --id req123456
```

You can find the request ID by using the `list_requests` command.

### Declining a Sharing Request

As a secondary user, you can decline a sharing request:

```bash
esp-rainmaker-cli sharing decline --id <request_id>
```

Example:
```bash
esp-rainmaker-cli sharing decline --id req123456
```

### Canceling a Sharing Request

As a primary user, you can cancel a pending sharing request:

```bash
esp-rainmaker-cli sharing cancel --id <request_id>
```

Example:
```bash
esp-rainmaker-cli sharing cancel --id req123456
```

### Listing Node Sharing Details

You can list sharing details for all nodes associated with your account:

```bash
esp-rainmaker-cli sharing list_nodes
```

To get sharing details for a specific node:

```bash
esp-rainmaker-cli sharing list_nodes --node <nodeid>
```

Example:
```bash
esp-rainmaker-cli sharing list_nodes --node abcd1234
```

### Listing Pending Requests

As a secondary user, to list sharing requests you've received:

```bash
esp-rainmaker-cli sharing list_requests
```

As a primary user, to list sharing requests you've sent:

```bash
esp-rainmaker-cli sharing list_requests --primary_user
```

To get details for a specific request:

```bash
esp-rainmaker-cli sharing list_requests --id <request_id>
```

Example:
```bash
esp-rainmaker-cli sharing list_requests --primary_user --id req123456
```

## Sharing Workflow Example

### Primary User:
1. Share a node with a secondary user:
   ```bash
   esp-rainmaker-cli sharing add_user --user secondary@example.com --nodes abcd1234
   ```

2. Check the status of the sharing request:
   ```bash
   esp-rainmaker-cli sharing list_requests --primary_user
   ```

3. If needed, cancel the request:
   ```bash
   esp-rainmaker-cli sharing cancel --id req123456
   ```

### Secondary User:
1. Check for received sharing requests:
   ```bash
   esp-rainmaker-cli sharing list_requests
   ```

2. Accept the sharing request:
   ```bash
   esp-rainmaker-cli sharing accept --id req123456
   ```

3. Verify the shared node is accessible:
   ```bash
   esp-rainmaker-cli getnodes
   esp-rainmaker-cli getnodedetails --nodeid abcd1234
   ```

## Notes

- The primary user must initiate sharing requests
- Secondary users can only accept or decline received requests
- Sharing requests expire after 7 days
- A primary user can revoke sharing at any time using the `remove_user` command
- Multiple secondary users can be added to the same node 