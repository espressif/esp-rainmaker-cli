# Node Cache and Session Reuse

## Overview

The ESP RainMaker CLI includes an optional caching layer that dramatically improves performance for local control operations. When enabled, the cache stores node details, configuration, POP (Proof of Possession), local control capability, and session crypto state on disk. This eliminates redundant cloud API calls, enables session reuse across CLI invocations, and auto-discovers nodes that support Security 0 local control.

Cache is **disabled by default** and must be explicitly enabled.

## What Gets Cached

| File | Description | TTL |
|------|-------------|-----|
| `node_details.json` | Full node details from cloud API | 1 hour |
| `node_config.json` | Node configuration | 1 hour |
| `local_control_info.json` | POP, security version, transport, port | 1 hour |
| `local_control_capability.json` | Empirically discovered sec0/sec1 support | 24 hours |
| `session.json` | AES-CTR crypto state, resolved IP, cookie | 7 days |

## Enabling Cache

Cache can be enabled at multiple levels:

### Profile Level

Enable cache when creating a new profile:

```bash
esp-rainmaker-cli profile add my-profile --base-url https://api.example.com/ --cache
```

Enable cache on an existing profile:

```bash
esp-rainmaker-cli cache enable
```

Disable cache on the current profile:

```bash
esp-rainmaker-cli cache disable
```

### Environment Variable

Override the profile setting for all commands in the current shell:

```bash
# Enable cache regardless of profile setting
export RM_NODE_CACHE=1

# Disable cache regardless of profile setting
export RM_NODE_CACHE=0
```

### Per-Command Override

Skip cache for a single command using `--no-cache`:

```bash
esp-rainmaker-cli getparams <nodeid> --local --no-cache
```

### Resolution Order

The cache-enabled decision follows this priority (highest to lowest):

1. `--no-cache` flag (always wins)
2. `RM_NODE_CACHE` environment variable
3. Profile configuration (`cache enable` / `profile add --cache`)
4. Default: disabled

## Cache Management Commands

### Show Cache Contents

```bash
# Show all cached nodes for the current profile/user
esp-rainmaker-cli cache show

# Show cache for a specific node
esp-rainmaker-cli cache show --nodeid <nodeid>
```

### Clear Cache

```bash
# Clear all cached data for the current profile/user
esp-rainmaker-cli cache clear

# Clear cache for a specific node only
esp-rainmaker-cli cache clear --nodeid <nodeid>
```

### Enable/Disable

```bash
esp-rainmaker-cli cache enable
esp-rainmaker-cli cache disable
```

## How Each Command Uses Cache

### Commands That Populate Cache

| Command | Caches |
|---------|--------|
| `getnodedetails` | node_details, local_control_info (POP) |
| `getnodeconfig` | node_config |
| `getnodeconfig --local` | node_config |
| `getparams` (cloud) | local_control_info (POP) |
| `getparams --local` | local_control_info (POP), session, capability |
| `setparams --local` | session, capability |

### Commands That Read From Cache

| Command | Reads |
|---------|-------|
| `getparams --local` | POP (from local_control_info or capability), session (for reuse) |
| `setparams --local` | POP, session |
| `getnodeconfig --local` | POP, session |
| `getparams --auto` | POP, session, capability |
| `setparams --auto` | POP, session, capability |
| `getnodeconfig --auto` | POP, session, capability |

## Session Reuse

Session reuse is the most impactful optimization. Without it, every `--local` command performs a full X25519 key exchange handshake. With session reuse, the saved crypto state is restored from disk and a lightweight probe verifies the session is alive.

### How It Works

1. After a successful local control operation, the CLI saves the session crypto state (shared key, nonce, AES-CTR counter offset, HTTP cookie) and the **resolved IP address** to disk.
2. On the next invocation, the CLI loads the saved state, reconstructs the AES-CTR cipher, connects directly to the saved IP (skipping mDNS resolution), and sends a lightweight probe to verify the session.
3. If the probe succeeds, the operation proceeds immediately -- no handshake, no mDNS.
4. If the probe fails (device rebooted, IP changed), the CLI automatically falls back to a fresh session establishment.

### Performance Impact

| Scenario | Without Cache | With Cache |
|----------|:---:|:---:|
| `getparams --local` (first time) | ~10s | ~10s (mDNS + handshake) |
| `getparams --local` (subsequent) | ~10s | **< 1s** (cached IP + session) |
| `setparams --local` (subsequent) | ~10s | **< 1s** |
| Cloud `getparams` (reference) | ~1.5s | ~1.5s |

### What Triggers a Fresh Session

- **Device reboot**: Session probe fails, fresh handshake is performed automatically.
- **Device IP change**: TCP connection to cached IP fails (3-second timeout), falls back to mDNS resolution.
- **`cache clear`**: Manually removes saved sessions.
- **7-day TTL expiry**: Sessions unused for 7 days are considered expired.

In all cases, the fallback is automatic and transparent.

## Capability Discovery

For nodes that support local control with **Security 0** but do not advertise a "Local Control" service in their cloud configuration (no POP field), the CLI can empirically discover this capability:

1. When `--local` is used with cache enabled, no POP is available, and no cached capability exists, the CLI enters discovery mode.
2. It first attempts a Security 0 connection (no POP required). If the device responds, it records `sec_ver=0, pop_required=false`.
3. If Security 0 fails and a POP is available, it tries Security 1.
4. The discovered capability is cached in `local_control_capability.json` (24-hour TTL), so subsequent commands skip the probe entirely.

This means you can use `--local` on Security 0 nodes without needing to specify `--sec_ver 0` manually, as long as cache is enabled.

## Storage Layout

```
~/.espressif/rainmaker/node_cache/
└── <profile_name>/
    └── <user_id>/
        ├── <nodeid_1>/
        │   ├── node_details.json
        │   ├── node_config.json
        │   ├── local_control_info.json
        │   ├── local_control_capability.json
        │   ├── session.json
        │   └── cache_meta.json
        └── <nodeid_2>/
            └── ...
```

Each node has its own directory. Cache is scoped by profile and user ID, so switching users or profiles never mixes data.

## Custom Cache Directory

By default, cache is stored under `~/.espressif/rainmaker/node_cache/`. You can override this with an environment variable:

```bash
export RM_NODE_CACHE_DIR=/path/to/custom/cache
```

This is useful for CI/CD pipelines or containerized environments where `~/.espressif` may not be appropriate.

## Environment Variables Summary

| Variable | Values | Description |
|----------|--------|-------------|
| `RM_NODE_CACHE` | `0` or `1` | Override profile cache setting |
| `RM_NODE_CACHE_DIR` | path | Override cache storage location |

## Troubleshooting

### Session resume is slow or failing

Clear the session cache to force a fresh connection:

```bash
esp-rainmaker-cli cache clear --nodeid <nodeid>
```

### Stale data after firmware update

If a device's configuration changed after a firmware update, clear its cache:

```bash
esp-rainmaker-cli cache clear --nodeid <nodeid>
```

### Cache is enabled but not being used

Check the resolution order:
1. Is `--no-cache` being passed?
2. Is `RM_NODE_CACHE=0` set in the environment?
3. Run `esp-rainmaker-cli cache show` to verify cache is active.

### Debug logging

Use `--debug` to see cache-related log messages:

```bash
esp-rainmaker-cli getparams <nodeid> --local --debug
```

Look for messages like:
- `Using cached POP for node ...`
- `Attempting session resume to ...`
- `Session resumed for node ...`
- `Saved session with resolved IP ...`
