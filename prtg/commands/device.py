"""Device commands for PRTG CLI."""

import sys
import click
from prtg.client import PRTGClientError, PRTGNotFoundError


@click.group(name="device")
def device():
    """Manage PRTG devices."""
    pass


@device.command(name="list")
@click.option(
    "--filter",
    "filter_regex",
    help="Filter by device name (regex)",
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
    "--group",
    "filter_group",
    help="Filter by parent group ID",
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
def device_list(
    ctx,
    filter_regex,
    status,
    filter_tag,
    filter_group,
    limit,
    offset,
):
    """List devices with optional filtering."""
    # Initialize client
    ctx.init_client()

    try:
        if ctx.verbose:
            click.echo("[INFO] Fetching devices...", err=True)

        # Get devices from API
        devices = ctx.client.get_devices(
            filter_status=status,
            filter_tags=filter_tag,
            filter_group=filter_group,
            count=limit,
            start=offset,
        )

        # Apply regex filter on client side (PRTG API doesn't support regex)
        if filter_regex:
            import re

            pattern = re.compile(filter_regex)
            devices.devices = [
                d for d in devices.devices if pattern.search(d.name or "")
            ]

        if ctx.verbose:
            click.echo(f"[INFO] Found {devices.total} device(s)", err=True)

        # Format and output
        output = ctx.formatter.format_devices(devices)
        click.echo(output)

    except PRTGClientError as e:
        error_output = ctx.formatter.format_error(e)
        click.echo(error_output, err=True)
        sys.exit(2)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)


@device.command(name="get")
@click.argument("device_ids", nargs=-1, required=True)
@click.option(
    "--stdin",
    is_flag=True,
    help="Read device IDs from stdin (one per line)",
)
@click.pass_obj
def device_get(ctx, device_ids, stdin):
    """Get detailed information about specific device(s)."""
    # Initialize client
    ctx.init_client()

    try:
        # Read from stdin if requested
        if stdin:
            device_ids = [line.strip() for line in sys.stdin if line.strip()]

        if not device_ids:
            click.echo("[ERROR] No device IDs provided", err=True)
            sys.exit(1)

        if ctx.verbose:
            click.echo(f"[INFO] Fetching {len(device_ids)} device(s)...", err=True)

        # Get devices
        if len(device_ids) == 1:
            # Single device
            device = ctx.client.get_device(device_ids[0])
            output = ctx.formatter.format_device(device)
            click.echo(output)
        else:
            # Multiple devices
            devices = ctx.client.get_devices_by_ids(list(device_ids))

            if not devices:
                click.echo("[WARN] No devices found", err=True)
                sys.exit(0)

            if ctx.verbose:
                click.echo(f"[INFO] Found {len(devices)} device(s)", err=True)

            # Create DeviceListResponse for consistent formatting
            from prtg.models.device import DeviceListResponse

            devices_response = DeviceListResponse(devices=devices)
            output = ctx.formatter.format_devices(devices_response)
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


@device.command(name="move")
@click.argument("device_ids", nargs=-1, required=False)
@click.option(
    "--stdin",
    is_flag=True,
    help="Read device IDs from stdin (one per line)",
)
@click.option(
    "--target-group",
    required=True,
    help="Target group ID to move devices to",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be moved without actually moving",
)
@click.pass_obj
def device_move(ctx, device_ids, stdin, target_group, dry_run):
    """Move device(s) to a different group.

    Examples:
        # Move single device
        prtg device move 2001 --target-group 5666

        # Move multiple devices
        prtg device move 2001 2002 2003 --target-group 5666

        # Move devices from stdin
        prtg device list --filter "^test-.*" | jq -r '.[].objid' | prtg device move --stdin --target-group 5666

        # Dry-run to preview changes
        prtg device move 2001 --target-group 5666 --dry-run
    """
    # Initialize client
    ctx.init_client()

    try:
        # Read from stdin if requested
        if stdin:
            device_ids = [line.strip() for line in sys.stdin if line.strip()]

        if not device_ids:
            click.echo("[ERROR] No device IDs provided", err=True)
            sys.exit(1)

        if ctx.verbose:
            click.echo(f"[INFO] Moving {len(device_ids)} device(s) to group {target_group}...", err=True)

        if dry_run:
            click.echo("[INFO] DRY-RUN MODE: No changes will be made", err=True)
            for device_id in device_ids:
                click.echo(f"[INFO] Would move device {device_id} to group {target_group}", err=True)
            sys.exit(0)

        # Move devices
        results = ctx.client.move_devices(list(device_ids), target_group)

        # Count successes and failures
        success_count = sum(1 for r in results if r["success"])
        failure_count = len(results) - success_count

        if ctx.verbose:
            click.echo(f"[INFO] Moved {success_count} device(s), {failure_count} failed", err=True)

        # Format and output results
        output = ctx.formatter.format_move_results(results)
        click.echo(output)

        # Exit with error code if any failures
        if failure_count > 0:
            sys.exit(3)

    except PRTGClientError as e:
        error_output = ctx.formatter.format_error(e)
        click.echo(error_output, err=True)
        sys.exit(2)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)
