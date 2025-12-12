"""Sensor commands for PRTG CLI."""

import sys
import click
from prtg.client import PRTGClientError, PRTGNotFoundError


@click.group(name="sensor")
def sensor():
    """Manage PRTG sensors."""
    pass


@sensor.command(name="list")
@click.option(
    "--filter",
    "filter_regex",
    help="Filter by sensor name (regex)",
)
@click.option(
    "--status",
    type=click.Choice(["up", "down", "warning", "paused", "unusual", "unknown"], case_sensitive=False),
    help="Filter by status",
)
@click.option(
    "--tag",
    "filter_tag",
    help="Filter by tag",
)
@click.option(
    "--device",
    "filter_device",
    help="Filter by parent device ID",
)
@click.option(
    "--limit",
    type=int,
    help="Limit number of results",
)
@click.option(
    "--offset",
    type=int,
    help="Offset for pagination",
)
@click.pass_obj
def sensor_list(
    ctx,
    filter_regex,
    status,
    filter_tag,
    filter_device,
    limit,
    offset,
):
    """List sensors with optional filtering."""
    # Initialize client
    ctx.init_client()

    try:
        if ctx.verbose:
            click.echo("[INFO] Fetching sensors...", err=True)

        # Get sensors from API
        sensors = ctx.client.get_sensors(
            filter_status=status,
            filter_tags=filter_tag,
            filter_device=filter_device,
            count=limit,
            start=offset,
        )

        # Apply regex filter on client side (PRTG API doesn't support regex)
        if filter_regex:
            import re

            pattern = re.compile(filter_regex)
            sensors.sensors = [
                s for s in sensors.sensors if pattern.search(s.name or "")
            ]

        if ctx.verbose:
            click.echo(f"[INFO] Found {sensors.total} sensor(s)", err=True)

        # Format and output
        output = ctx.formatter.format_sensors(sensors)
        click.echo(output)

    except PRTGClientError as e:
        error_output = ctx.formatter.format_error(e)
        click.echo(error_output, err=True)
        sys.exit(2)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)


@sensor.command(name="get")
@click.argument("sensor_ids", nargs=-1, required=True)
@click.option(
    "--stdin",
    is_flag=True,
    help="Read sensor IDs from stdin (one per line)",
)
@click.pass_obj
def sensor_get(ctx, sensor_ids, stdin):
    """Get detailed information about specific sensor(s)."""
    # Initialize client
    ctx.init_client()

    try:
        # Read from stdin if requested
        if stdin:
            sensor_ids = [line.strip() for line in sys.stdin if line.strip()]

        if not sensor_ids:
            click.echo("[ERROR] No sensor IDs provided", err=True)
            sys.exit(1)

        if ctx.verbose:
            click.echo(f"[INFO] Fetching {len(sensor_ids)} sensor(s)...", err=True)

        # Get sensors
        if len(sensor_ids) == 1:
            # Single sensor
            sensor = ctx.client.get_sensor(sensor_ids[0])
            output = ctx.formatter.format_sensor(sensor)
            click.echo(output)
        else:
            # Multiple sensors
            sensors = ctx.client.get_sensors_by_ids(list(sensor_ids))

            if not sensors:
                click.echo("[WARN] No sensors found", err=True)
                sys.exit(0)

            if ctx.verbose:
                click.echo(f"[INFO] Found {len(sensors)} sensor(s)", err=True)

            # Create SensorListResponse for consistent formatting
            from prtg.models.sensor import SensorListResponse

            sensors_response = SensorListResponse(sensors=sensors)
            output = ctx.formatter.format_sensors(sensors_response)
            click.echo(output)

    except PRTGNotFoundError as e:
        if ctx.verbose:
            click.echo(f"[ERROR] {e}", err=True)
        error_output = ctx.formatter.format_error(e)
        click.echo(error_output, err=True)
        sys.exit(4)
    except PRTGClientError as e:
        error_output = ctx.formatter.format_error(e)
        click.echo(error_output, err=True)
        sys.exit(2)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)


@sensor.command(name="data")
@click.argument("sensor_id", required=True)
@click.option(
    "--days",
    type=int,
    help="Get last N days of data (default: 7, max: 40 for raw data)",
)
@click.option(
    "--hours",
    type=int,
    help="Get last N hours of data",
)
@click.option(
    "--start",
    "start_date",
    help="Start date/time (format: yyyy-MM-dd-HH-mm-ss)",
)
@click.option(
    "--end",
    "end_date",
    help="End date/time (format: yyyy-MM-dd-HH-mm-ss)",
)
@click.option(
    "--interval",
    type=click.Choice(["raw", "1m", "1h", "1d"], case_sensitive=False),
    default="raw",
    help="Averaging interval (default: raw)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["csv", "json"], case_sensitive=False),
    default="csv",
    help="Output format (default: csv)",
)
@click.option(
    "--output",
    "output_file",
    type=click.Path(),
    help="Save to file instead of stdout",
)
@click.option(
    "--head",
    type=int,
    help="Limit output to last N rows (default: 50 for CSV to terminal, 0 for all)",
)
@click.pass_obj
def sensor_data(
    ctx,
    sensor_id,
    days,
    hours,
    start_date,
    end_date,
    interval,
    output_format,
    output_file,
    head,
):
    """Get historic data for a sensor.

    Retrieve time-series sensor measurements over a specified time range.
    Data can be returned as raw values or averaged over intervals.

    When outputting CSV to terminal (no --output), only the last 50 rows are shown
    by default. Use --head N to change the limit, or --output to save all data to a file.

    Examples:

      # Last 50 rows of last 7 days (default)
      prtg sensor data 2460

      # Show last 20 rows
      prtg sensor data 2460 --head 20

      # Show all data (no limit)
      prtg sensor data 2460 --head 0

      # Save full 7 days to file (no limit applied)
      prtg sensor data 2460 --output sensor.csv

      # Last 24 hours in JSON format (no limit for JSON)
      prtg sensor data 2460 --hours 24 --format json

      # Specific date range with hourly averages, saved to file
      prtg sensor data 2460 --start 2024-01-01-00-00-00 --end 2024-01-31-23-59-59 --interval 1h --output data.csv

    Note: PRTG limits historic data to 40 days for raw data and 500 days for averaged data.
    Rate limit: 5 requests per minute.
    """
    from datetime import datetime, timedelta

    # Initialize client
    ctx.init_client()

    try:
        # Calculate date range
        if start_date and end_date:
            # Use explicit dates
            sdate = start_date
            edate = end_date
        elif days:
            # Calculate from days
            end = datetime.now()
            start = end - timedelta(days=days)
            sdate = start.strftime("%Y-%m-%d-%H-%M-%S")
            edate = end.strftime("%Y-%m-%d-%H-%M-%S")
        elif hours:
            # Calculate from hours
            end = datetime.now()
            start = end - timedelta(hours=hours)
            sdate = start.strftime("%Y-%m-%d-%H-%M-%S")
            edate = end.strftime("%Y-%m-%d-%H-%M-%S")
        else:
            # Default: last 7 days
            end = datetime.now()
            start = end - timedelta(days=7)
            sdate = start.strftime("%Y-%m-%d-%H-%M-%S")
            edate = end.strftime("%Y-%m-%d-%H-%M-%S")

        # Map interval to seconds
        interval_map = {
            "raw": 0,
            "1m": 60,
            "1h": 3600,
            "1d": 86400,
        }
        avg_interval = interval_map[interval.lower()]

        # Validate date range based on interval
        if start_date and end_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d-%H-%M-%S")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d-%H-%M-%S")
            delta_days = (end_dt - start_dt).days

            if avg_interval == 0 and delta_days > 40:
                click.echo(
                    "[ERROR] Raw data is limited to 40 days. "
                    "Use --interval 1h or 1d for longer ranges.",
                    err=True
                )
                sys.exit(5)
            elif delta_days > 500:
                click.echo(
                    "[ERROR] Historic data is limited to 500 days maximum.",
                    err=True
                )
                sys.exit(5)

        if ctx.verbose:
            click.echo(f"[INFO] Fetching sensor data from {sdate} to {edate}...", err=True)
            click.echo(f"[INFO] Averaging interval: {interval}", err=True)
            click.echo(f"[INFO] Format: {output_format}", err=True)

        # Get historic data
        result = ctx.client.get_sensor_historicdata(
            sensor_id=sensor_id,
            start_date=sdate,
            end_date=edate,
            avg_interval=avg_interval,
            output_format=output_format,
        )

        # Output result
        if output_format == "csv":
            output = result

            # Apply row limiting for CSV to terminal (not to file)
            if not output_file:
                # Determine limit: use --head value or default to 50
                limit = head if head is not None else 50

                if limit > 0:
                    # Split CSV into lines, keep header + last N data rows
                    lines = output.strip().split('\n')
                    if len(lines) > 1:  # Has header + data
                        header = lines[0]
                        data_lines = lines[1:]

                        if len(data_lines) > limit:
                            # Take last N rows
                            limited_lines = data_lines[-limit:]
                            output = '\n'.join([header] + limited_lines) + '\n'

                            # Show warning about limiting
                            total_rows = len(data_lines)
                            click.echo(
                                f"[INFO] Showing last {limit} of {total_rows} rows "
                                f"(use --head N or --output to change)",
                                err=True
                            )
        else:  # json
            import json
            output = json.dumps(result, indent=2 if ctx.formatter.pretty else None)

        # Write to file or stdout
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            if ctx.verbose:
                click.echo(f"[INFO] Data saved to {output_file}", err=True)
        else:
            click.echo(output)

    except PRTGNotFoundError as e:
        if ctx.verbose:
            click.echo(f"[ERROR] {e}", err=True)
        error_output = ctx.formatter.format_error(e)
        click.echo(error_output, err=True)
        sys.exit(4)
    except PRTGClientError as e:
        error_output = ctx.formatter.format_error(e)
        click.echo(error_output, err=True)
        sys.exit(2)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)
