# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Installation
```bash
# Install all dependencies (including dev dependencies)
uv sync --all-extras

# Sync after updating pyproject.toml
uv sync --all-extras
```

### Testing
```bash
# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_sensor.py

# Run specific test class
uv run pytest tests/test_sensor.py::TestSensorModel

# Run specific test method
uv run pytest tests/test_sensor.py::TestSensorModel::test_basic_sensor_creation

# Run with coverage
uv run pytest --cov=prtg --cov-report=html
```

### Running the CLI
```bash
# Run from source (development mode)
uv run prtg --help
uv run prtg device list
uv run prtg sensor list

# Or activate the virtual environment first
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate    # Windows
prtg --help
```

### Adding Dependencies
```bash
# Add a new runtime dependency
uv add package-name

# Add a new dev dependency
uv add --dev package-name

# Remove a dependency
uv remove package-name
```

## Architecture Overview

### High-Level Design Patterns

**Unix Philosophy**: The CLI is designed to be composable and pipe-friendly. All commands output JSON that can be processed with `jq`, `grep`, and other Unix tools. Commands use stdin/stdout for data flow.

**Test-Driven Development (TDD)**: This codebase strictly follows TDD. When adding new features:
1. Write test fixtures first (tests/fixtures/)
2. Write tests that fail
3. Implement the feature to make tests pass
4. Refactor if needed

### Core Architecture Components

#### 1. CLI Layer (prtg/cli.py)
- **Context Pattern**: Uses Click's context object to share state (config, client, formatter) across commands
- **Lazy Initialization**: Client is initialized on first use via `ctx.init_client()` to avoid unnecessary API connections
- **Command Registration**: Commands are registered at the bottom of cli.py using `cli.add_command()`
- **Pretty Printing**: JSON output is pretty-printed by default (`--pretty/--no-pretty`, default: True) for better readability and jq piping

#### 2. Command Pattern (prtg/commands/)
Each command file (device.py, sensor.py, group.py) follows the same structure:
- `@click.group(name="...")` for the command group
- `@click.pass_obj` to receive the Context object
- `command_list()` - List resources with filtering
- `command_get()` - Get specific resources by ID with stdin support

All commands:
- Call `ctx.init_client()` before using the API
- Use `ctx.formatter.format_*()` for output
- Handle errors with specific exit codes (0=success, 2=API error, 4=not found)
- Support `--stdin` flag for bulk operations via pipes

#### 3. API Client Layer (prtg/client.py)
- **Single Responsibility**: One method per API endpoint
- **Consistent Method Naming**: `get_<entity>()`, `get_<entity>s()`, `get_<entities>_by_ids()`
- **PRTG API Pattern**: All queries use `table.json` endpoint with `content` parameter (devices, sensors, groups)
- **Error Hierarchy**: PRTGClientError (base) → PRTGAuthenticationError, PRTGNotFoundError, PRTGAPIError
- **Status Mapping**: Friendly names (up, down) are mapped to PRTG raw codes (3, 5)

#### 4. Pydantic Models (prtg/models/)
Uses **Pydantic v2.12+** with modern patterns:

**Base Model Hierarchy**:
- `PRTGBaseModel` - Base configuration (ignore extra fields, strip whitespace)
- `PRTGObjectModel` - Common fields (objid, name, tags) with validators
- `PRTGStatusMixin` - Status-related fields
- `PRTGPriorityMixin` - Priority fields
- `PRTGListResponse` - Base for list responses (prtg-version, treesize)

**Key Patterns**:
- Use `model_config` dict (not Config class) for Pydantic v2
- Use `@field_validator(mode="before")` for pre-processing
- Convert numeric IDs to strings for consistency
- Parse space-separated tags to lists
- Use `Field(...)` for required fields, `Field(None, ...)` for optional
- Use `model_dump(exclude_none=True)` for serialization

**Mixin Pattern**: Models inherit from multiple mixins (Device = PRTGObjectModel + PRTGStatusMixin + PRTGPriorityMixin) to share common fields.

#### 5. Formatter Strategy Pattern (prtg/formatters/)
- **Factory Pattern**: FormatterFactory manages formatter registration
- **Strategy Pattern**: Abstract Formatter base class with concrete implementations (JSONFormatter)
- **Registration**: Formatters self-register at module load: `FormatterFactory.register("json", JSONFormatter)`

To add a new formatter:
1. Implement abstract methods from Formatter base class
2. Call `FormatterFactory.register()` at module level
3. Formatters are automatically available via `--output` flag

#### 6. Configuration Precedence (prtg/config.py)
Configuration is loaded in strict order (highest priority first):
1. CLI arguments (--url, --api-token)
2. Environment variables (PRTG_URL, PRTG_API_TOKEN)
3. .env file in current directory
4. Config file (~/.config/prtg/config)
5. Defaults

**API Token Priority**: PRTG_API_TOKEN > PRTG_API_TOKEN_RW > PRTG_API_TOKEN_RO

### Adding a New Command (e.g., "probe")

Follow this exact pattern (proven with sensor implementation):

1. **Create test fixtures**: `tests/fixtures/probes.json` with realistic API response
2. **Write model tests**: `tests/test_probe.py` - test Pydantic model validation
3. **Implement models**: `prtg/models/probe.py` - Probe and ProbeListResponse
4. **Write client tests**: Add tests to `tests/test_probe.py` for API methods
5. **Implement client**: Add methods to `prtg/client.py` (get_probes, get_probe, get_probes_by_ids)
6. **Add formatter methods**: Update `prtg/formatters/base.py` (abstract) and `prtg/formatters/json.py` (implementation)
7. **Implement commands**: Create `prtg/commands/probe.py` with list/get commands
8. **Register command**: Add to `prtg/cli.py` imports and `cli.add_command(probe.probe)`
9. **Update README**: Add probe examples to Commands section

### PRTG API Patterns

**All entities use table.json endpoint**:
```python
params = {
    "content": "sensors",  # or "devices", "groups", "probes"
    "columns": "objid,name,status,...",  # comma-separated
    "filter_status": "3",  # status codes (not names)
    "filter_tags": "@tag(production)",  # tag filter format
    "filter_objid": "2460",  # for single object queries
    "count": "*",  # get all (or specific number)
    "start": 0,  # pagination offset
}
```

**Status Code Mapping**:
- Up: "3"
- Down: "5"
- Warning: "4"
- Paused: "7"
- Unusual: "10"
- Unknown: "1"

### Historic Data API Pattern

**For time-series sensor measurements**, use the `historicdata` endpoint:

```python
# Endpoint format
endpoint = f"historicdata.{format}"  # format: "csv" or "json"

params = {
    "id": "2460",  # sensor ID
    "sdate": "2024-01-01-00-00-00",  # start date
    "edate": "2024-01-31-23-59-59",  # end date
    "avg": 0,  # averaging interval in seconds
}
```

**Date Format**: `yyyy-MM-dd-HH-mm-ss` (e.g., "2024-01-15-14-30-00")

**Averaging Interval Mapping**:
- Raw data: `0`
- 1 minute: `60`
- 1 hour: `3600`
- 1 day: `86400`

**Important Limits**:
- **Rate Limit**: 5 requests per minute (returns HTTP 429 if exceeded)
- **Raw Data**: Maximum 40 days
- **Averaged Data**: Maximum 500 days
- Always validate date ranges before making API calls

**Response Format**:
- **CSV**: Returns raw CSV string with headers (datetime, value columns)
- **JSON**: Returns dict with `{"histdata": [...], "sensorid": "2460"}` structure

**Example Implementation Pattern**:

```python
def get_sensor_historicdata(
    self,
    sensor_id: str,
    start_date: str,
    end_date: str,
    avg_interval: int = 0,
    output_format: str = "csv",
):
    """Get historic time-series data for a sensor."""
    endpoint = f"historicdata.{output_format}"
    params = {
        "id": sensor_id,
        "sdate": start_date,
        "edate": end_date,
        "avg": avg_interval,
    }

    response = self._make_request("GET", endpoint, params=params)

    # Handle rate limiting specifically
    if response.status_code == 429:
        raise PRTGAPIError(
            "Rate limit exceeded (5 requests per minute for historic data). "
            "Please wait 60 seconds before trying again."
        )

    # Return appropriate format
    if output_format == "csv":
        return response.text  # Raw CSV string
    else:
        return response.json()  # Parsed JSON dict
```

**CLI Command Pattern**:
- Time range options: `--days`, `--hours`, or `--start`/`--end`
- Averaging: `--interval` (raw, 1m, 1h, 1d)
- Output: `--format` (csv, json), `--output` (file path)
- Row limiting: `--head N` to limit terminal output (default: 50 for CSV, 0 for all)
- Validate date ranges before API call (exit code 5 for validation errors)

**Output Limiting Pattern** (for commands with potentially large output):
- Default: Show last 50 rows when outputting CSV to terminal (no `--output` file)
- Add `--head N` option to allow user control (0 = no limit)
- File output: Never apply limits when using `--output` (user wants full data)
- JSON format: No limits (users pipe to jq for processing)
- Show info message to stderr: `[INFO] Showing last N of M rows (use --head N or --output to change)`

```python
# Example implementation in CLI command
if output_format == "csv" and not output_file:
    limit = head if head is not None else 50  # Default to 50 rows
    if limit > 0:
        lines = output.strip().split('\n')
        if len(lines) > 1:  # Has header + data
            header = lines[0]
            data_lines = lines[1:]
            if len(data_lines) > limit:
                limited_lines = data_lines[-limit:]  # Take last N rows
                output = '\n'.join([header] + limited_lines) + '\n'
                click.echo(f"[INFO] Showing last {limit} of {len(data_lines)} rows", err=True)
```

### Exit Codes Convention
- `0` - Success
- `1` - General error
- `2` - API error / Connection error
- `3` - Authentication error (currently unused, was for move operations)
- `4` - Resource not found
- `5` - Validation error

### Test Organization
Each entity has one test file (e.g., `tests/test_sensor.py`) containing:
- `TestSensorModel` - Pydantic model validation tests
- `TestSensorListResponse` - List response model tests
- `TestPRTGClientSensors` - API client method tests (mocked)

**Fixtures**: All test fixtures in `tests/fixtures/` use realistic PRTG API response format.

**Mocking**: Use `@patch("requests.Session.request")` to mock HTTP calls, return fixture data.

### Design Principles (from README)
1. **Unix Philosophy**: Do one thing well, composable commands
2. **Strategy Pattern**: Formatters for easy extension (JSON, future: CSV, TSV)
3. **Factory Pattern**: Client creation and formatters
4. **TDD Approach**: Tests written alongside implementation
5. **Pydantic Models**: Type-safe schemas with validation
6. **YAGNI**: Implement only what's needed now

### Python Version & Dependencies
- **Python**: 3.14+ (required)
- **Pydantic**: 2.12.0+ (uses v2 patterns)
- **Click**: CLI framework
- **Requests**: HTTP client
- **python-dotenv**: .env file support
