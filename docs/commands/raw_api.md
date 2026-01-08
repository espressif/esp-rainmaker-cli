# Raw API Command

The `raw-api` command lets you send arbitrary REST requests to the ESP RainMaker backend using the same authenticated session as the rest of the CLI. It is ideal when you need to experiment with new endpoints, debug backend issues, or unblock yourself before high-level CLI support exists.

## Command Syntax

```bash
esp-rainmaker-cli raw-api \
  --method <GET|POST|PUT|DELETE|PATCH> \
  --api <path> \
  [--query-params key=value&flag=true] \
  [--body '{"json":true}'] \
  [--body-file payload.json] \
  [--profile <name>]
```

### Required Arguments
- `--method`: HTTP verb to use. Options: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`.
- `--api`: API path relative to the RainMaker host configured in the active profile. You can pass values with or without `/v1/` (e.g., `user/nodes` or `/v1/user/nodes`).

### Optional Arguments
- `--query-params`: Raw query string appended to the request, without the leading `?`. Example: `node_details=true&node_id=abcdef`.
- `--body`: JSON string sent as the request body. Useful for quick tests.
- `--body-file`: Path to a file that contains JSON to send as the request body. Use when payloads are large; mutually exclusive with `--body`.
- `--profile`: CLI profile to use for authentication and region selection. Defaults to the current profile.

> **Note:** You must be logged in (have an authenticated session) for the RainMaker backend to accept the request. The command prints the resolved request URL, HTTP status code, and attempts to pretty-print JSON responses.

## Examples

### GET node list with query parameters
```bash
esp-rainmaker-cli raw-api \
  --method GET \
  --api user/nodes \
  --query-params node_details=true
```

### POST with inline JSON body
```bash
esp-rainmaker-cli raw-api \
  --method POST \
  --api user/nodes/commands \
  --body '{"node_id":"abcd1234","command":"blink"}'
```

### PUT using a payload file and a different profile
```bash
esp-rainmaker-cli raw-api \
  --method PUT \
  --api /v1/user/nodes/metadata \
  --body-file ./payloads/update_metadata.json \
  --profile staging
```

## Tips and Troubleshooting
- Use `--body` for simple payloads; prefer `--body-file` for complex JSON to avoid shell-escaping issues.
- The CLI automatically prepends the base host from the selected profile, so you only need to provide the path (e.g., `user/nodes`).
- If both `--body` and `--body-file` are supplied, the command exits with an error—pass only one.
- Non-JSON responses are printed as plain text to help debug raw errors from the backend or proxy servers.
- HTTPS certificate verification uses the same trust store as other CLI commands; SSL errors usually indicate profile misconfiguration or intercepted traffic.
