# PRTG CLI Design Document

## Philosophy & Design Principles

### Unix Philosophy
1. **Do one thing well**: Each command has a single, clear purpose
2. **Text streams**: All output is parseable text (JSON/CSV/TSV)
3. **Composable**: Commands pipe to each other and standard Unix tools
4. **Silent success**: Only output data, not status messages (unless verbose)
5. **Meaningful exit codes**: 0 for success, non-zero for errors
6. **Config files**: Support standard config file locations

### CLI Best Practices
- Use `--long-options` and `-s` short options
- Support `--help` at every level
- Read from stdin when appropriate (for bulk operations)
- Support `--dry-run` for destructive operations
- Implement `--filter` for client-side filtering beyond API
- Support `--no-header` for CSV/TSV output (better for piping)

---

## Command Structure

```
prtg [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGS]
```

### Global Options
```
--url TEXT          PRTG server URL (or PRTG_URL env var)
--username TEXT     Username (or PRTG_USERNAME env var)
--passhash TEXT     Password hash (or PRTG_PASSHASH env var)
--config FILE       Config file path (default: ~/.config/prtg/config)
--output FORMAT     Output format: json, csv, tsv, table, jq (default: json)
--no-header         Suppress header row in CSV/TSV output
--pretty            Pretty-print JSON output
--verbose, -v       Verbose output (to stderr)
--debug             Debug mode (show API calls)
--no-verify-ssl     Disable SSL verification
--profile TEXT      Use named profile from config file
```

### Configuration File Format
```ini
# ~/.config/prtg/config

[default]
url = https://prtg.example.com
username = admin
passhash = 1234567890
verify_ssl = false

[production]
url = https://prtg-prod.example.com
username = api_user
passhash = abcdef123456
verify_ssl = true

[staging]
url = https://prtg-staging.example.com
username = api_user
passhash = fedcba654321
```

---

## Core Commands

### 1. Device Management

#### `prtg device list`
List devices with optional filtering

**Usage:**
```bash
prtg device list [OPTIONS]

Options:
  --filter REGEX          Filter by device name (regex)
  --group TEXT            Filter by group name/ID
  --status TEXT           Filter by status (up|down|warning|paused|unusual|unknown)
  --tag TEXT              Filter by tag (can be specified multiple times)
  --limit INT             Limit number of results
  --offset INT            Offset for pagination
  --sort-by TEXT          Sort by field (name|status|id|lastup)
  --order TEXT            Sort order (asc|desc)
```

**Output Schema (JSON):**
```json
[
  {
    "objid": "2001",
    "device": "web-server-01",
    "group": "Web Servers",
    "probe": "Local Probe",
    "host": "192.168.1.10",
    "status": "Up",
    "status_raw": "3",
    "message": "",
    "lastup": "2025-11-05 10:30:00",
    "lastdown": "2025-11-01 03:15:00",
    "uptime": "4d 7h 15m",
    "uptime_seconds": 375300,
    "tags": ["production", "web", "linux"],
    "priority": "3",
    "comments": "Main web server",
    "location": "Rack 4, Position 12"
  }
]
```

**Examples:**
```bash
# List all devices
prtg device list

# List devices matching regex
prtg device list --filter "web-.*-prod"

# List only devices that are down
prtg device list --status down

# Output as CSV without header (for piping)
prtg device list --output csv --no-header

# Get device IDs only (using jq)
prtg device list | jq -r '.[].objid'

# Parallel processing with xargs
prtg device list --filter "web-.*" --output csv --no-header | \
  cut -d',' -f1 | \
  xargs -P 10 -I {} prtg sensor list --device {}
```

---

#### `prtg device get`
Get detailed information about specific device(s)

**Usage:**
```bash
prtg device get [OPTIONS] DEVICE_ID [DEVICE_ID...]

Options:
  --by-name              Treat arguments as device names instead of IDs
  --stdin                Read device IDs from stdin (one per line)
```

**Output Schema (JSON):**
```json
[
  {
    "objid": "2001",
    "device": "web-server-01",
    "group": "Web Servers",
    "probe": "Local Probe",
    "host": "192.168.1.10",
    "icon": "device_linux.png",
    "status": "Up",
    "status_raw": "3",
    "message": "",
    "lastup": "2025-11-05 10:30:00",
    "lastdown": "2025-11-01 03:15:00",
    "uptime": "4d 7h 15m",
    "uptime_seconds": 375300,
    "downtime": "2h 15m",
    "downtime_seconds": 8100,
    "uptime_percent": "99.95",
    "tags": ["production", "web", "linux"],
    "priority": "3",
    "priority_raw": "3",
    "comments": "Main web server",
    "location": "Rack 4, Position 12",
    "dependencies": [],
    "schedule": "Always",
    "access_rights": "Full",
    "sensor_count": 15,
    "sensor_count_up": 14,
    "sensor_count_down": 1,
    "sensor_count_warning": 0,
    "sensor_count_unusual": 0,
    "sensor_count_paused": 0
  }
]
```

**Examples:**
```bash
# Get single device by ID
prtg device get 2001

# Get multiple devices
prtg device get 2001 2002 2003

# Get device by name
prtg device get web-server-01 --by-name

# Pipe from list command
prtg device list --status down | jq -r '.[].objid' | prtg device get --stdin

# Compare two devices side-by-side
diff <(prtg device get 2001 --output json --pretty) \
     <(prtg device get 2002 --output json --pretty)
```

---

#### `prtg device duplicates`
Find duplicate devices (same IP or hostname)

**Usage:**
```bash
prtg device duplicates [OPTIONS]

Options:
  --by TEXT              Check duplicates by: ip, hostname, both (default: both)
  --show-diff            Show detailed diff between duplicates
  --ignore-paused        Ignore paused devices
```

**Output Schema (JSON):**
```json
[
  {
    "duplicate_key": "192.168.1.10",
    "duplicate_type": "ip",
    "devices": [
      {
        "objid": "2001",
        "device": "web-server-01",
        "host": "192.168.1.10",
        "status": "Up",
        "group": "Web Servers"
      },
      {
        "objid": "2002",
        "device": "web-server-01-old",
        "host": "192.168.1.10",
        "status": "Paused",
        "group": "Legacy"
      }
    ],
    "diff": {
      "status": ["Up", "Paused"],
      "group": ["Web Servers", "Legacy"],
      "tags": [["production", "web"], ["legacy"]],
      "lastup": ["2025-11-05 10:30:00", "2025-10-15 14:20:00"]
    }
  }
]
```

**Examples:**
```bash
# Find all duplicates
prtg device duplicates

# Find only IP duplicates
prtg device duplicates --by ip

# Show detailed diff
prtg device duplicates --show-diff

# Get IDs of duplicate devices (keep first, delete others)
prtg device duplicates --output json | \
  jq -r '.[] | .devices[1:] | .[].objid' | \
  xargs -I {} prtg device delete {} --dry-run
```

---

#### `prtg device create`
Create a new device

**Usage:**
```bash
prtg device create [OPTIONS] NAME

Options:
  --host TEXT              IP address or hostname (required)
  --group TEXT             Parent group name or ID (required)
  --template TEXT          Device template to use
  --tags TEXT              Comma-separated tags
  --priority INT           Priority (1-5)
  --location TEXT          Physical location
  --comments TEXT          Comments
  --stdin                  Read JSON configuration from stdin
  --dry-run                Show what would be created without creating
```

**Input Schema (JSON via stdin):**
```json
{
  "device": "web-server-03",
  "host": "192.168.1.12",
  "group": "2000",
  "tags": ["production", "web", "linux"],
  "priority": 3,
  "location": "Rack 4, Position 14",
  "comments": "New web server",
  "template": "Linux Server Template"
}
```

**Output Schema (JSON):**
```json
{
  "objid": "2003",
  "device": "web-server-03",
  "status": "created",
  "message": "Device created successfully"
}
```

**Examples:**
```bash
# Create device with options
prtg device create web-server-03 \
  --host 192.168.1.12 \
  --group "Web Servers" \
  --tags production,web,linux \
  --priority 3

# Bulk create from JSON file
cat devices.json | prtg device create --stdin

# Create from CSV with parallel processing
cat devices.csv | tail -n +2 | \
  parallel --colsep ',' \
    prtg device create {1} --host {2} --group {3}
```

---

#### `prtg device update`
Update device properties

**Usage:**
```bash
prtg device update [OPTIONS] DEVICE_ID [DEVICE_ID...]

Options:
  --name TEXT              New device name
  --host TEXT              New IP/hostname
  --tags TEXT              New tags (comma-separated, replaces existing)
  --add-tag TEXT           Add tag (can be specified multiple times)
  --remove-tag TEXT        Remove tag
  --priority INT           Priority (1-5)
  --location TEXT          Physical location
  --comments TEXT          Comments
  --status TEXT            Status (pause|resume)
  --stdin                  Read updates from stdin (JSON)
  --dry-run                Show what would be updated
```

**Examples:**
```bash
# Update single device
prtg device update 2001 --name web-server-01-new --tags production,web

# Pause multiple devices
prtg device update 2001 2002 2003 --status pause

# Bulk update from JSON
echo '[
  {"objid": "2001", "priority": 1, "tags": ["critical", "production"]},
  {"objid": "2002", "priority": 2, "tags": ["production"]}
]' | prtg device update --stdin

# Add tag to all web servers
prtg device list --filter "web-.*" | jq -r '.[].objid' | \
  xargs -I {} prtg device update {} --add-tag monitored
```

---

#### `prtg device delete`
Delete device(s)

**Usage:**
```bash
prtg device delete [OPTIONS] DEVICE_ID [DEVICE_ID...]

Options:
  --by-name              Treat arguments as device names
  --stdin                Read device IDs from stdin
  --force                Skip confirmation prompt
  --dry-run              Show what would be deleted
```

**Examples:**
```bash
# Delete single device (with confirmation)
prtg device delete 2001

# Delete multiple devices without confirmation
prtg device delete 2001 2002 2003 --force

# Delete all paused devices (dry-run first!)
prtg device list --status paused | jq -r '.[].objid' | \
  prtg device delete --stdin --dry-run

# Then actually delete
prtg device list --status paused | jq -r '.[].objid' | \
  prtg device delete --stdin --force
```

---

### 2. Sensor Management

#### `prtg sensor list`
List sensors with filtering

**Usage:**
```bash
prtg sensor list [OPTIONS]

Options:
  --device TEXT           Filter by device name/ID
  --filter REGEX          Filter by sensor name (regex)
  --type TEXT             Filter by sensor type
  --status TEXT           Filter by status
  --tag TEXT              Filter by tag
  --limit INT             Limit results
  --offset INT            Offset for pagination
  --sort-by TEXT          Sort field
  --show-channels         Include channel information
```

**Output Schema (JSON):**
```json
[
  {
    "objid": "3001",
    "sensor": "Ping",
    "device": "web-server-01",
    "device_id": "2001",
    "type": "ping",
    "type_raw": "ping",
    "status": "Up",
    "status_raw": "3",
    "message": "OK",
    "lastvalue": "5 ms",
    "lastvalue_raw": "5.234",
    "lastup": "2025-11-05 10:30:00",
    "lastdown": "2025-11-01 03:15:00",
    "uptime": "4d 7h 15m",
    "downtime": "2h 15m",
    "uptime_percent": "99.95",
    "priority": "3",
    "tags": ["network", "icmp"],
    "interval": "60",
    "interval_text": "60 seconds"
  }
]
```

**Examples:**
```bash
# List all sensors for a device
prtg sensor list --device 2001

# List sensors matching pattern
prtg sensor list --filter "Disk.*C:"

# List all down sensors
prtg sensor list --status down

# Get sensor IDs for bulk operations
prtg sensor list --device 2001 --output csv --no-header | \
  cut -d',' -f1
```

---

#### `prtg sensor get`
Get detailed sensor information

**Usage:**
```bash
prtg sensor get [OPTIONS] SENSOR_ID [SENSOR_ID...]

Options:
  --stdin                Read sensor IDs from stdin
  --show-channels        Include channel data
  --show-history         Include historical data summary
```

**Output Schema (JSON):**
```json
{
  "objid": "3001",
  "sensor": "Ping",
  "device": "web-server-01",
  "device_id": "2001",
  "type": "ping",
  "status": "Up",
  "status_raw": "3",
  "message": "OK",
  "lastvalue": "5 ms",
  "lastvalue_raw": "5.234",
  "lastup": "2025-11-05 10:30:00",
  "lastdown": "2025-11-01 03:15:00",
  "uptime_percent": "99.95",
  "priority": "3",
  "tags": ["network", "icmp"],
  "interval": "60",
  "schedule": "Always",
  "dependency": null,
  "channels": [
    {
      "channel": "Ping Time",
      "lastvalue": "5 ms",
      "lastvalue_raw": "5.234"
    },
    {
      "channel": "Packet Loss",
      "lastvalue": "0 %",
      "lastvalue_raw": "0"
    }
  ]
}
```

---

#### `prtg sensor create`
Create a new sensor

**Usage:**
```bash
prtg sensor create [OPTIONS] NAME

Options:
  --device TEXT           Device name or ID (required)
  --type TEXT             Sensor type (required)
  --stdin                 Read JSON configuration from stdin
  --dry-run               Show what would be created
```

**Examples:**
```bash
# Create ping sensor
prtg sensor create "Ping" --device 2001 --type ping

# Bulk create sensors from JSON
cat sensors.json | prtg sensor create --stdin
```

---

#### `prtg sensor update`
Update sensor properties

**Usage:**
```bash
prtg sensor update [OPTIONS] SENSOR_ID [SENSOR_ID...]

Options:
  --name TEXT             New sensor name
  --interval INT          Scanning interval (seconds)
  --tags TEXT             New tags
  --add-tag TEXT          Add tag
  --remove-tag TEXT       Remove tag
  --priority INT          Priority
  --status TEXT           Status (pause|resume)
  --stdin                 Read updates from stdin
  --dry-run               Show changes
```

---

#### `prtg sensor delete`
Delete sensor(s)

**Usage:**
```bash
prtg sensor delete [OPTIONS] SENSOR_ID [SENSOR_ID...]

Options:
  --stdin                Read sensor IDs from stdin
  --force                Skip confirmation
  --dry-run              Show what would be deleted
```

---

#### `prtg sensor pause`
Pause sensor(s) with optional message

**Usage:**
```bash
prtg sensor pause [OPTIONS] SENSOR_ID [SENSOR_ID...]

Options:
  --message TEXT         Pause message
  --duration INT         Pause duration in minutes (default: indefinite)
  --stdin                Read sensor IDs from stdin
```

**Examples:**
```bash
# Pause sensor with message
prtg sensor pause 3001 --message "Maintenance window"

# Pause for 30 minutes
prtg sensor pause 3001 --duration 30

# Pause all sensors on a device during maintenance
prtg sensor list --device 2001 | jq -r '.[].objid' | \
  prtg sensor pause --stdin --message "Server maintenance" --duration 60
```

---

#### `prtg sensor resume`
Resume paused sensor(s)

**Usage:**
```bash
prtg sensor resume [OPTIONS] SENSOR_ID [SENSOR_ID...]

Options:
  --stdin                Read sensor IDs from stdin
```

---

### 3. Group Management

#### `prtg group list`
List groups

**Usage:**
```bash
prtg group list [OPTIONS]

Options:
  --filter REGEX         Filter by group name
  --parent TEXT          Filter by parent group
  --limit INT            Limit results
```

**Output Schema (JSON):**
```json
[
  {
    "objid": "1000",
    "group": "Web Servers",
    "probe": "Local Probe",
    "parent": "Root",
    "parent_id": "0",
    "device_count": 5,
    "sensor_count": 45,
    "status": "Up",
    "tags": ["production"]
  }
]
```

---

#### `prtg group get`
Get group details

#### `prtg group create`
Create new group

#### `prtg group update`
Update group properties

#### `prtg group delete`
Delete group

---

### 4. Historical Data & Reports

#### `prtg history`
Get historical sensor data

**Usage:**
```bash
prtg history [OPTIONS] SENSOR_ID

Options:
  --start TEXT           Start date/time (ISO format or relative: -1d, -2h)
  --end TEXT             End date/time (default: now)
  --channel TEXT         Specific channel name
  --avg INT              Average interval in seconds
  --format TEXT          Output format: json, csv, tsv, influx, prometheus
```

**Output Schema (JSON):**
```json
[
  {
    "datetime": "2025-11-05T10:00:00Z",
    "datetime_raw": "44950.4166666667",
    "value": "5.234",
    "value_text": "5 ms",
    "coverage": "100%",
    "coverage_raw": "100"
  }
]
```

**Examples:**
```bash
# Get last 24 hours of data
prtg history 3001 --start -24h

# Get data for specific date range
prtg history 3001 --start 2025-11-01 --end 2025-11-05

# Export to CSV for analysis
prtg history 3001 --start -7d --output csv > sensor_data.csv

# Get data and pipe to gnuplot
prtg history 3001 --start -24h --output tsv | \
  gnuplot -e "set terminal dumb; plot '-' using 1:2 with lines"

# Export in InfluxDB line protocol
prtg history 3001 --start -1d --format influx

# Export in Prometheus format
prtg history 3001 --start -1h --format prometheus
```

---

### 5. Status & Monitoring

#### `prtg status`
Get overall PRTG status

**Usage:**
```bash
prtg status [OPTIONS]

Options:
  --detailed             Include detailed statistics
```

**Output Schema (JSON):**
```json
{
  "version": "21.4.73",
  "activation_status": "Licensed",
  "devices_total": 150,
  "devices_up": 145,
  "devices_down": 2,
  "devices_warning": 1,
  "devices_paused": 2,
  "sensors_total": 1250,
  "sensors_up": 1200,
  "sensors_down": 5,
  "sensors_warning": 15,
  "sensors_unusual": 3,
  "sensors_paused": 27,
  "alarms": 7,
  "messages": 2,
  "tickets": 3,
  "cluster_status": "Master",
  "readonly": false
}
```

---

#### `prtg alarms`
List active alarms

**Usage:**
```bash
prtg alarms [OPTIONS]

Options:
  --priority INT         Filter by priority
  --since TEXT           Show alarms since date/time
  --limit INT            Limit results
```

---

#### `prtg messages`
List system messages

---

### 6. Notifications & Alerts

#### `prtg notification list`
List notification templates

#### `prtg notification create`
Create notification template

#### `prtg notification update`
Update notification template

---

### 7. Tags

#### `prtg tag list`
List all tags in use

**Output Schema (JSON):**
```json
[
  {
    "tag": "production",
    "count": 45
  },
  {
    "tag": "linux",
    "count": 23
  }
]
```

---

#### `prtg tag add`
Add tag to objects

**Usage:**
```bash
prtg tag add TAG [OPTIONS]

Options:
  --device TEXT          Device ID(s)
  --sensor TEXT          Sensor ID(s)
  --group TEXT           Group ID(s)
  --stdin                Read object IDs from stdin
```

**Examples:**
```bash
# Add tag to multiple devices
prtg tag add monitored --device 2001 2002 2003

# Add tag to all devices in a group
prtg device list --group "Web Servers" | jq -r '.[].objid' | \
  prtg tag add production --stdin
```

---

#### `prtg tag remove`
Remove tag from objects

---

### 8. Utilities

#### `prtg config`
Manage configuration

**Usage:**
```bash
prtg config [SUBCOMMAND]

Subcommands:
  init                   Create default config file
  show                   Show current configuration
  test                   Test connection to PRTG server
  profiles               List available profiles
```

**Examples:**
```bash
# Initialize config
prtg config init

# Test connection
prtg config test

# Test specific profile
prtg config test --profile production
```

---

#### `prtg export`
Export PRTG configuration

**Usage:**
```bash
prtg export [OPTIONS]

Options:
  --type TEXT            Export type: devices, sensors, groups, all
  --output FILE          Output file (default: stdout)
  --format TEXT          Format: json, yaml, csv
```

---

#### `prtg import`
Import PRTG configuration

**Usage:**
```bash
prtg import [OPTIONS] FILE

Options:
  --type TEXT            Import type: devices, sensors, groups
  --dry-run              Validate without importing
  --skip-existing        Skip existing objects
  --update-existing      Update existing objects
```

---

## Advanced Usage Patterns

### 1. Parallel Processing
```bash
# Process devices in parallel
prtg device list --status up | jq -r '.[].objid' | \
  parallel -j 10 'prtg sensor list --device {} --output json >> all_sensors.json'

# Bulk pause with GNU parallel
cat device_ids.txt | \
  parallel -j 5 prtg device update {} --status pause --message "Maintenance"
```

### 2. Pipeline Composition
```bash
# Find devices with down sensors and email report
prtg sensor list --status down | \
  jq -r '.[] | "\(.device) - \(.sensor)"' | \
  mail -s "Down Sensors Report" admin@example.com

# Export device inventory to Excel-compatible CSV
prtg device list --output csv | \
  iconv -f UTF-8 -t UTF-16LE | \
  sed 's/$/\r/' > devices_excel.csv
```

### 3. Monitoring Integration
```bash
# Check for down devices (Nagios-style exit code)
prtg sensor list --status down --output json | \
  jq -e 'length == 0' || exit 2

# Export metrics to Prometheus
while true; do
  prtg sensor list --output json | \
    jq -r '.[] | "prtg_sensor_status{device=\"\(.device)\",sensor=\"\(.sensor)\"} \(.status_raw)"' > \
    /var/lib/prometheus/node_exporter/prtg.prom
  sleep 60
done
```

### 4. Backup & Restore
```bash
# Daily backup
prtg export --type all --format json | \
  gzip > "prtg_backup_$(date +%Y%m%d).json.gz"

# Restore from backup
gunzip -c prtg_backup_20251105.json.gz | \
  prtg import --type all --skip-existing
```

### 5. Bulk Operations
```bash
# Create 100 devices from template
for i in {1..100}; do
  echo "server-$i,192.168.1.$i,Web Servers"
done | prtg device create --stdin

# Update all Linux devices
prtg device list --filter ".*linux.*" | \
  jq -r '.[].objid' | \
  xargs -I {} prtg device update {} --add-tag linux-monitored
```

---

## Output Format Specifications

### JSON (default)
```json
[{"objid": "2001", "device": "web-server-01", ...}]
```

### JSON Pretty (`--pretty`)
```json
[
  {
    "objid": "2001",
    "device": "web-server-01",
    ...
  }
]
```

### CSV
```csv
objid,device,host,status,group
2001,web-server-01,192.168.1.10,Up,Web Servers
```

### CSV (no header)
```csv
2001,web-server-01,192.168.1.10,Up,Web Servers
```

### TSV
```tsv
objid	device	host	status	group
2001	web-server-01	192.168.1.10	Up	Web Servers
```

### Table (human-readable)
```
┌───────┬───────────────┬──────────────┬────────┬─────────────┐
│ objid │ device        │ host         │ status │ group       │
├───────┼───────────────┼──────────────┼────────┼─────────────┤
│ 2001  │ web-server-01 │ 192.168.1.10 │ Up     │ Web Servers │
└───────┴───────────────┴──────────────┴────────┴─────────────┘
```

### JQ (pre-formatted for jq)
Output optimized for jq processing with common fields flattened

---

## Exit Codes

```
0   - Success
1   - General error
2   - API error / Connection error
3   - Authentication error
4   - Not found (device/sensor/group doesn't exist)
5   - Validation error (invalid input)
6   - Permission denied
```

---

## Environment Variables

```bash
PRTG_URL              # PRTG server URL
PRTG_USERNAME         # Username
PRTG_PASSHASH         # Password hash
PRTG_CONFIG           # Config file path
PRTG_PROFILE          # Profile name to use
PRTG_OUTPUT_FORMAT    # Default output format
PRTG_NO_VERIFY_SSL    # Set to '1' to disable SSL verification
PRTG_DEBUG            # Set to '1' for debug mode
```

---

## Error Handling

### Standard Error Output
All error messages, warnings, and verbose output go to stderr:
```bash
[ERROR] Device not found: 9999
[WARN] SSL verification disabled
[INFO] Processing 50 devices...
```

### Progress Indicators
For long-running operations (only when stderr is a TTY):
```bash
Processing devices: [████████████████────────] 67% (100/150)
```

---

## Performance Considerations

1. **Pagination**: Use `--limit` and `--offset` for large datasets
2. **Parallel requests**: Use GNU parallel or xargs -P
3. **Caching**: Consider implementing client-side caching for reference data
4. **Batch operations**: Prefer bulk operations over loops when possible
5. **Output format**: JSON is fastest; table format is slowest

---

## Future Enhancements

### Phase 2
- `prtg watch` - Real-time monitoring of sensors/devices
- `prtg diff` - Compare device/sensor configurations
- `prtg clone` - Clone device with all sensors
- `prtg report` - Generate formatted reports
- `prtg template` - Template management

### Phase 3
- Interactive TUI mode (`prtg tui`)
- WebSocket support for real-time updates
- Local caching with TTL
- Plugin system for custom commands
- Shell completion (bash/zsh/fish)

---

## Testing Strategy

### Unit Tests
- API client methods
- Output formatters
- Input validators

### Integration Tests
- Test against PRTG demo server
- Mock API responses
- CLI argument parsing

### End-to-End Tests
```bash
# Test device lifecycle
device_id=$(prtg device create test-device --host 1.2.3.4 --group Test | jq -r '.objid')
prtg device get $device_id
prtg device update $device_id --tags test
prtg device delete $device_id --force
```

---

## Dependencies

### Required
- Python 3.8+
- requests
- click
- tabulate

### Optional
- jq (for advanced JSON processing)
- parallel (for parallel operations)
- rich (for enhanced terminal output)
- PyYAML (for YAML support)

---

## Documentation

### Man Page
```bash
man prtg
man prtg-device
man prtg-sensor
```

### Built-in Help
```bash
prtg --help
prtg device --help
prtg device list --help
```

### Examples
```bash
prtg examples                    # List all examples
prtg examples device             # Device-specific examples
prtg examples parallel           # Parallel processing examples
```
