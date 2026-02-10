# Node Tags and Metadata

## Overview

ESP RainMaker allows you to attach **tags** and **metadata** to nodes. Tags are simple key-value labels useful for categorization and filtering, while metadata is freeform JSON data for storing custom information about a node.

Tags and metadata can be:
- **Set during provisioning** (at mapping time, via the `provision` command)
- **Managed on existing nodes** (via the `node` command)

## The `node` Command

The `node` command provides subcommands for managing tags and metadata on existing nodes.

```bash
esp-rainmaker-cli node --help
```

### Add Tags

Add tags to a node. Tags must be in `key:value` format.

```bash
esp-rainmaker-cli node add-tags <nodeid> --tags <tags>
```

**Parameters:**
- `<nodeid>`: Node ID (required)
- `--tags`: Comma-separated list of tags in `key:value` format (required)

**Examples:**
```bash
# Add a single tag
esp-rainmaker-cli node add-tags mynode123 --tags "location:pune"

# Add multiple tags
esp-rainmaker-cli node add-tags mynode123 --tags "location:pune,name:espressif,env:production"
```

### Remove Tags

Remove specific tags from a node.

```bash
esp-rainmaker-cli node remove-tags <nodeid> --tags <tags>
```

**Parameters:**
- `<nodeid>`: Node ID (required)
- `--tags`: Comma-separated list of tags to remove (required)

**Examples:**
```bash
# Remove a single tag
esp-rainmaker-cli node remove-tags mynode123 --tags "location:pune"

# Remove multiple tags
esp-rainmaker-cli node remove-tags mynode123 --tags "location:pune,env:production"
```

### Set Metadata

Set or update metadata for a node. Metadata follows shadow-style merge rules:
- New keys are added, existing keys are updated
- Setting a key to `null` deletes that specific key
- Arrays are overwritten (not merged)

```bash
esp-rainmaker-cli node set-metadata <nodeid> --data <json>
esp-rainmaker-cli node set-metadata <nodeid> --filepath <path>
```

**Parameters:**
- `<nodeid>`: Node ID (required)
- `--data`: Metadata as a JSON string (mutually exclusive with `--filepath`)
- `--filepath`: Path to a JSON file containing metadata (mutually exclusive with `--data`)

**Examples:**
```bash
# Set metadata using inline JSON
esp-rainmaker-cli node set-metadata mynode123 --data '{"serial_no": "abc123", "region": "us"}'

# Set metadata from a file
esp-rainmaker-cli node set-metadata mynode123 --filepath metadata.json

# Update a specific key (other keys are preserved)
esp-rainmaker-cli node set-metadata mynode123 --data '{"region": "eu"}'

# Delete a specific key by setting it to null
esp-rainmaker-cli node set-metadata mynode123 --data '{"region": null}'
```

### Delete Metadata

Delete metadata from a node. Without `--key`, deletes all metadata. With `--key`, deletes only the specified key(s).

```bash
esp-rainmaker-cli node delete-metadata <nodeid> [--key <keys>]
```

**Parameters:**
- `<nodeid>`: Node ID (required)
- `--key`: Comma-separated list of metadata keys to delete (optional; if omitted, all metadata is deleted)

**Examples:**
```bash
# Delete specific metadata keys
esp-rainmaker-cli node delete-metadata mynode123 --key "region,serial_no"

# Delete all metadata
esp-rainmaker-cli node delete-metadata mynode123
```

## Tags and Metadata During Provisioning

Tags and metadata can also be attached at the time of node mapping during provisioning. This works with all transport modes (BLE, SoftAP, on-network) and both mapping flows (traditional and challenge-response).

```bash
esp-rainmaker-cli provision [provisioning options] --tags <tags> --metadata <json>
```

**Parameters:**
- `--tags`: Comma-separated list of tags in `key:value` format
- `--metadata`: Metadata as a JSON string

**Examples:**
```bash
# BLE provisioning with tags and metadata
esp-rainmaker-cli provision --pop abcd1234 \
  --transport ble --device_name PROV_d76c30 \
  --tags "location:mumbai,env:production" \
  --metadata '{"serial_no": "abc123", "batch": "2026-Q1"}'

# On-network mapping with tags
esp-rainmaker-cli provision --transport on-network \
  --device-ip 192.168.1.50 --pop abcd1234 \
  --tags "esp.location:office"

# SoftAP provisioning with metadata only
esp-rainmaker-cli provision --pop abcd1234 \
  --transport softap \
  --metadata '{"firmware": "v2.0", "hw_rev": "B"}'
```

## Tag Format

Tags must follow the `key:value` format:
- Both key and value are strings
- Example valid tags: `location:pune`, `name:espressif`, `esp.location:mumbai`
- Invalid tags (missing colon) will be rejected by the API with error code `105046`

## Metadata Merge Rules

Metadata updates follow shadow-style merge semantics:

| Operation | Payload | Effect |
|-----------|---------|--------|
| Add/update keys | `{"key": "value"}` | Upserts the specified keys |
| Delete a key | `{"key": null}` | Removes that specific key |
| Delete all metadata | `null` (via `delete-metadata` without `--key`) | Removes all metadata |
| Overwrite array | `{"regions": ["a", "b"]}` | Replaces the entire array |
| Empty object | `{}` | No change |

## Viewing Tags and Metadata

Tags and metadata for a node are displayed by the `getnodedetails` command:

```bash
esp-rainmaker-cli getnodedetails <nodeid>
```

The output includes `Tags` and `Metadata` sections when they are set on a node.
