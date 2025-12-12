# Device Commands

The `device` command group provides operations for managing and querying PRTG devices.

## Commands

- [`device list`](#device-list) - List devices with filtering
- [`device get`](#device-get) - Get detailed device information

---

## device list

List all devices from PRTG with optional filtering.

### Usage

```bash
prtg device list [OPTIONS]
```

### Options

| Option | Type | Description |
|--------|------|-------------|
| `--filter TEXT` | String | Filter by device name using regex pattern |
| `--status [up\|down\|warning\|paused\|unusual\|unknown]` | Choice | Filter by device status |
| `--tag TEXT` | String | Filter by tag |
| `--group TEXT` | String | Filter by parent group ID |
| `--limit INTEGER` | Number | Limit number of results returned |
| `--offset INTEGER` | Number | Offset for pagination |

### Examples

**List all devices:**

```bash
prtg device list --url https://prtg.example.com --api-token YOUR_API_TOKEN_HERE
```

**List only devices that are down:**

```bash
prtg device list --status down
```

**Filter devices by name pattern:**

```bash
prtg device list --filter "web-.*-prod"
```

**List devices with a specific tag:**

```bash
prtg device list --tag production
```

**List devices in a specific group:**

```bash
prtg device list --group 1000
```

**Paginated results:**

```bash
# First 10 devices
prtg device list --limit 10 --offset 0

# Next 10 devices
prtg device list --limit 10 --offset 10
```

**Pretty-print JSON output:**

```bash
prtg device list --pretty
```

**Using configuration file:**

```bash
# Create config file first
prtg config init

# Edit ~/.config/prtg/config with your credentials
# Then use without credentials:
prtg device list
```

### Output Format

The command outputs a JSON array of device objects:

```json
[
  {
    "objid": "2001",
    "name": "web-server-01",
    "device": "web-server-01",
    "host": "192.168.1.10",
    "probe": "Local Probe",
    "group": "Web Servers",
    "parentid": "1000",
    "status": "Up",
    "status_raw": "3",
    "message": "OK",
    "tags": ["production", "web", "linux"],
    "priority": "3",
    "upsens": "10",
    "downsens": "0",
    "sensor_count_up": 10,
    "sensor_count_down": 0
  }
]
```

### Exit Codes

- `0` - Success
- `1` - General error
- `2` - API error / Connection error

---

## device get

Get detailed information about one or more specific devices.

### Usage

```bash
prtg device get [OPTIONS] DEVICE_ID [DEVICE_ID...]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `DEVICE_ID` | One or more device object IDs |

### Options

| Option | Type | Description |
|--------|------|-------------|
| `--stdin` | Flag | Read device IDs from stdin (one per line) |

### Examples

**Get a single device:**

```bash
prtg device get 2001
```

**Get multiple devices:**

```bash
prtg device get 2001 2002 2003
```

**Get device with pretty output:**

```bash
prtg device get 2001 --pretty
```

**Read device IDs from stdin:**

```bash
echo -e "2001\n2002\n2003" | prtg device get --stdin
```

**Pipe from device list:**

```bash
# Get all down devices, then get detailed info
prtg device list --status down | jq -r '.[].objid' | prtg device get --stdin
```

### Output Format

For a single device, outputs a JSON object:

```json
{
  "objid": "2001",
  "name": "web-server-01",
  "device": "web-server-01",
  "host": "192.168.1.10",
  "probe": "Local Probe",
  "group": "Web Servers",
  "status": "Up",
  "tags": ["production", "web"],
  "sensor_count_up": 10,
  "sensor_count_down": 0
}
```

For multiple devices, outputs a JSON array (same as `device list`).

### Exit Codes

- `0` - Success
- `1` - General error
- `2` - API error / Connection error
- `4` - Device not found

---

## Common Patterns

### Find all down devices

```bash
prtg device list --status down
```

### Get specific fields using jq

```bash
# Get just device IDs and names
prtg device list | jq -r '.[] | "\(.objid): \(.name)"'

# Get devices with sensor counts
prtg device list | jq -r '.[] | select(.sensor_count_down > 0) | "\(.name): \(.sensor_count_down) down"'
```

### Filter by regex pattern

```bash
# All web servers in production
prtg device list --filter "web-.*-prod"

# All database servers
prtg device list --filter "db-.*"
```

### Combining filters

```bash
# Production web servers that are down
prtg device list --filter "web-.*" --tag production --status down
```

---

## Configuration

### Using Environment Variables

```bash
export PRTG_URL=https://prtg.example.com
export PRTG_API_TOKEN=YOUR_API_TOKEN_HERE

prtg device list  # Uses env vars
```

Or use a `.env` file:

```bash
PRTG_URL=https://prtg.example.com
PRTG_API_TOKEN=YOUR_API_TOKEN_HERE
```

### Using Configuration File

Create `~/.config/prtg/config`:

```ini
[default]
url = https://prtg.example.com
api_token = YOUR_API_TOKEN_HERE
verify_ssl = true

[production]
url = https://prtg-prod.example.com
api_token = YOUR_PRODUCTION_API_TOKEN
# Or use separate RO/RW tokens
# api_token_ro = YOUR_READ_ONLY_TOKEN
# api_token_rw = YOUR_READ_WRITE_TOKEN
```

Then use with profiles:

```bash
# Uses default profile
prtg device list

# Uses production profile
prtg device list --profile production
```

### Precedence

Configuration values are resolved in this order (highest to lowest):

1. Command-line arguments
2. Environment variables
3. `.env` file in current directory
4. Configuration file (`~/.config/prtg/config`)
5. Defaults

---

## Notes

- Device IDs (objid) are always strings, not integers
- Tags are returned as arrays, even if empty
- Sensor counts ending in `_raw` are strings from the API
- Sensor counts ending in `_count` are converted to integers for convenience
- The `--filter` option uses Python regex patterns (client-side filtering)
- All other filters are applied server-side by the PRTG API
