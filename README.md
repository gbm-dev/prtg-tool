# PRTG CLI Tool

A command-line interface for PRTG Network Monitor API, designed following Unix philosophy for automation and scripting.

## Features

- **Simple & Focused**: Start with device management (`list`, `get`)
- **JSON Output**: Structured, parseable output for automation
- **Composable**: Pipe-friendly design for use with jq, grep, and other Unix tools
- **Configurable**: Support for config files, environment variables, and profiles
- **Type-Safe**: Built with Pydantic for validated schemas
- **Well-Tested**: Comprehensive test suite with 75+ tests

## Installation

### From Source

```bash
git clone https://github.com/yourusername/prtg-tool.git
cd prtg-tool
pip install -e .
```

### Development Installation

```bash
pip install -e ".[dev]"
```

## Quick Start

### Basic Usage

```bash
# List all devices
prtg device list \
  --url https://prtg.example.com \
  --api-token YOUR_API_TOKEN_HERE

# Get a specific device
prtg device get 2001 --url https://prtg.example.com --api-token YOUR_API_TOKEN_HERE

# JSON is pretty-printed by default (use --no-pretty for compact output)
prtg device list
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

Then use without credentials:

```bash
# Uses default profile
prtg device list

# Uses production profile
prtg device list --profile production
```

### Using Environment Variables

```bash
export PRTG_URL=https://prtg.example.com
export PRTG_API_TOKEN=YOUR_API_TOKEN_HERE

prtg device list  # Uses environment variables
```

### Using .env File

Create a `.env` file in your project directory:

```bash
PRTG_URL=https://prtg.example.com
PRTG_API_TOKEN=YOUR_API_TOKEN_HERE

# Optional: Separate RO/RW tokens (RW takes priority)
# PRTG_API_TOKEN_RO=YOUR_READ_ONLY_TOKEN
# PRTG_API_TOKEN_RW=YOUR_READ_WRITE_TOKEN

# Optional settings
# PRTG_NO_VERIFY_SSL=1
# PRTG_DEBUG=1
```

See `.env.example` for a complete template.

## Commands

### Sensor Management

#### List Sensors

```bash
# List all sensors
prtg sensor list

# Filter by status
prtg sensor list --status down

# Filter by tag
prtg sensor list --tag production

# Filter by name pattern (regex)
prtg sensor list --filter "ping.*"

# Filter by parent device
prtg sensor list --device 2001

# Combine filters
prtg sensor list --status down --tag production --filter "ping.*"

# Pagination
prtg sensor list --limit 10 --offset 0
```

#### Get Sensor Details

```bash
# Single sensor
prtg sensor get 2460

# Multiple sensors
prtg sensor get 2460 2461 2462

# Read from stdin
echo "2460" | prtg sensor get --stdin

# Pipe from list
prtg sensor list --status down | jq -r '.[].objid' | prtg sensor get --stdin
```

#### Get Sensor Historic Data

**Note:** When outputting CSV to terminal, only the last 50 rows are shown by default to avoid overwhelming output. Use `--head N` to adjust or `--output file.csv` to save all data.

```bash
# Last 50 rows of last 7 days (default behavior)
prtg sensor data 2460

# Show last 20 rows
prtg sensor data 2460 --head 20

# Show all data (no limit)
prtg sensor data 2460 --head 0

# Last 24 hours in JSON format (no row limit for JSON)
prtg sensor data 2460 --hours 24 --format json

# Last 30 days with daily averages, limited to 50 rows
prtg sensor data 2460 --days 30 --interval 1d

# Specific date range with hourly averages
prtg sensor data 2460 --start 2024-01-01-00-00-00 --end 2024-01-31-23-59-59 --interval 1h

# Save full 7 days to file (no row limit when saving to file)
prtg sensor data 2460 --days 7 --output sensor_2460.csv

# Get raw data for last 7 days, all rows
prtg sensor data 2460 --days 7 --interval raw --head 0
```

### Device Management

#### List Devices

```bash
# List all devices
prtg device list

# Filter by status
prtg device list --status down

# Filter by tag
prtg device list --tag production

# Filter by name pattern (regex)
prtg device list --filter "web-.*-prod"

# Combine filters
prtg device list --status down --tag production --filter "web-.*"

# Pagination
prtg device list --limit 10 --offset 0
```

#### Get Device Details

```bash
# Single device
prtg device get 2001

# Multiple devices
prtg device get 2001 2002 2003

# Read from stdin
echo "2001" | prtg device get --stdin

# Pipe from list
prtg device list --status down | jq -r '.[].objid' | prtg device get --stdin
```

## Common Use Cases

### Find all down sensors

```bash
prtg sensor list --status down
```

### Get sensor details for a specific device

```bash
prtg sensor list --device 2001
```

### Find sensors with specific names

```bash
prtg sensor list | jq -r '.[] | select(.name | contains("Ping")) | "\(.objid): \(.name) - \(.device)"'
```

### Monitor critical sensors

```bash
#!/bin/bash
# Check if critical sensors are up
CRITICAL_SENSORS="2460 2461 2462"

for sensor_id in $CRITICAL_SENSORS; do
  status=$(prtg sensor get $sensor_id | jq -r '.status')
  if [ "$status" != "Up" ]; then
    echo "ALERT: Sensor $sensor_id is $status"
  fi
done
```

### Export sensors to CSV

```bash
prtg sensor list | jq -r '.[] | [.objid, .name, .device, .status, .lastvalue] | @csv' > sensors.csv
```

### Get sensor data for analysis

```bash
# Export last 30 days of ping data to CSV
prtg sensor data 2460 --days 30 --interval 1d --output ping_monthly.csv

# Get hourly CPU data for the last week in JSON
prtg sensor data 2480 --days 7 --interval 1h --format json > cpu_weekly.json

# Compare sensor performance
for sensor_id in 2460 2461 2462; do
  prtg sensor data $sensor_id --days 7 --output sensor_${sensor_id}.csv
done
```

### Find all down devices

```bash
prtg device list --status down
```

### Get device names and IDs

```bash
prtg device list | jq -r '.[] | "\(.objid): \(.name)"'
```

### Find devices with down sensors

```bash
prtg device list | jq -r '.[] | select(.sensor_count_down > 0) | "\(.name): \(.sensor_count_down) sensors down"'
```

### Export to CSV (using jq)

```bash
prtg device list | jq -r '.[] | [.objid, .name, .host, .status] | @csv' > devices.csv
```

### Monitor specific devices

```bash
#!/bin/bash
# Check if critical devices are up
CRITICAL_DEVICES="2001 2002 2003"

for device_id in $CRITICAL_DEVICES; do
  status=$(prtg device get $device_id | jq -r '.status')
  if [ "$status" != "Up" ]; then
    echo "ALERT: Device $device_id is $status"
  fi
done
```

## Configuration

### Configuration Precedence

Settings are loaded in this order (highest priority first):

1. Command-line arguments (`--url`, `--api-token`, etc.)
2. Environment variables (`PRTG_URL`, `PRTG_API_TOKEN`, etc.)
3. `.env` file in current directory
4. Configuration file (`~/.config/prtg/config`)
5. Defaults

### API Token Priority

When using multiple token options, priority is:

1. `PRTG_API_TOKEN` (or `--api-token`)
2. `PRTG_API_TOKEN_RW` (read-write token)
3. `PRTG_API_TOKEN_RO` (read-only token)
4. Config file: `api_token`, `api_token_rw`, `api_token_ro`

### Environment Variables

| Variable | Description |
|----------|-------------|
| `PRTG_URL` | PRTG server URL |
| `PRTG_API_TOKEN` | API authentication token (highest priority) |
| `PRTG_API_TOKEN_RW` | Read-write API token (fallback) |
| `PRTG_API_TOKEN_RO` | Read-only API token (fallback) |
| `PRTG_PROFILE` | Profile name to use from config file |
| `PRTG_CONFIG` | Path to config file |
| `PRTG_OUTPUT_FORMAT` | Output format (currently only `json`) |
| `PRTG_NO_VERIFY_SSL` | Set to `1` to disable SSL verification |
| `PRTG_DEBUG` | Set to `1` for debug output |

### Global Options

| Option | Description |
|--------|-------------|
| `--url TEXT` | PRTG server URL |
| `--api-token TEXT` | API authentication token |
| `--config PATH` | Config file path |
| `--profile TEXT` | Profile name from config file |
| `--no-verify-ssl` | Disable SSL verification |
| `--output [json]` | Output format (default: json) |
| `--pretty` / `--no-pretty` | Pretty-print JSON output (default: enabled) |
| `-v, --verbose` | Verbose output (to stderr) |
| `--debug` | Debug mode (show API calls) |

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=prtg --cov-report=html

# Run specific test file
pytest tests/test_client.py

# Verbose output
pytest -v
```

### Project Structure

```
prtg-tool/
├── prtg/
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   ├── cli.py               # Main CLI
│   ├── client.py            # PRTG API client
│   ├── config.py            # Configuration management
│   ├── models/              # Pydantic models
│   │   ├── base.py
│   │   └── device.py
│   ├── formatters/          # Output formatters
│   │   ├── base.py
│   │   └── json.py
│   └── commands/            # Command implementations
│       └── device.py
├── tests/                   # Test suite
├── docs/                    # Documentation
├── setup.py                 # Package configuration
└── README.md
```

### Design Principles

1. **Unix Philosophy**: Do one thing well, composable commands
2. **Strategy Pattern**: Formatters for easy extension (JSON, CSV, TSV)
3. **Factory Pattern**: API client creation and formatters
4. **TDD Approach**: Tests written alongside implementation
5. **Pydantic Models**: Type-safe schemas with validation
6. **YAGNI**: Implement only what's needed now

## API Reference

See [docs/commands/device.md](docs/commands/device.md) for detailed device command documentation.

## Getting Your API Token

1. Log in to PRTG web interface
2. Go to **Setup > My Account > API Keys**
3. Click **Add API Key** or use an existing key
4. Copy the API token value

**Note:** API tokens provide better security than username/passhash authentication:
- Tokens can be revoked without changing passwords
- You can create separate read-only and read-write tokens
- Tokens can be scoped with specific permissions

## Exit Codes

- `0` - Success
- `1` - General error
- `2` - API error / Connection error
- `3` - Authentication error
- `4` - Resource not found
- `5` - Validation error

## Limitations (Current Version)

This is the initial release focusing on device listing. Future versions will add:

- CSV/TSV output formats
- Sensor management commands
- Group management
- Device creation/update/delete
- Historical data queries
- Interactive TUI mode

## Contributing

Contributions are welcome! Please ensure:

1. All tests pass: `pytest`
2. Code follows existing patterns
3. New features include tests
4. Documentation is updated

## License

[Your License Here]

## Acknowledgments

Built with:
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [Requests](https://requests.readthedocs.io/) - HTTP client
- [Pytest](https://pytest.org/) - Testing framework
