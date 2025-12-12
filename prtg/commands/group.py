"""Group commands for PRTG CLI."""

import sys
import click
from prtg.client import PRTGClientError, PRTGNotFoundError


@click.group(name="group")
def group():
    """Manage PRTG groups."""
    pass


@group.command(name="list")
@click.option(
    "--filter",
    "filter_regex",
    help="Filter by group name (regex)",
)
@click.option(
    "--parent",
    "filter_parent",
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
def group_list(
    ctx,
    filter_regex,
    filter_parent,
    limit,
    offset,
):
    """List groups with optional filtering."""
    # Initialize client
    ctx.init_client()

    try:
        if ctx.verbose:
            click.echo("[INFO] Fetching groups...", err=True)

        # Get groups from API
        groups = ctx.client.get_groups(
            filter_parentid=filter_parent,
            count=limit,
            start=offset,
        )

        # Apply regex filter on client side (PRTG API doesn't support regex)
        if filter_regex:
            import re

            pattern = re.compile(filter_regex)
            groups.groups = [
                g for g in groups.groups if pattern.search(g.name or "")
            ]

        if ctx.verbose:
            click.echo(f"[INFO] Found {groups.total} group(s)", err=True)

        # Format and output
        output = ctx.formatter.format_groups(groups)
        click.echo(output)

    except PRTGClientError as e:
        error_output = ctx.formatter.format_error(e)
        click.echo(error_output, err=True)
        sys.exit(2)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)


@group.command(name="get")
@click.argument("group_ids", nargs=-1, required=True)
@click.option(
    "--stdin",
    is_flag=True,
    help="Read group IDs from stdin (one per line)",
)
@click.pass_obj
def group_get(ctx, group_ids, stdin):
    """Get detailed information about specific group(s)."""
    # Initialize client
    ctx.init_client()

    try:
        # Read from stdin if requested
        if stdin:
            group_ids = [line.strip() for line in sys.stdin if line.strip()]

        if not group_ids:
            click.echo("[ERROR] No group IDs provided", err=True)
            sys.exit(1)

        if ctx.verbose:
            click.echo(f"[INFO] Fetching {len(group_ids)} group(s)...", err=True)

        # Get groups
        if len(group_ids) == 1:
            # Single group
            group_obj = ctx.client.get_group(group_ids[0])
            output = ctx.formatter.format_group(group_obj)
            click.echo(output)
        else:
            # Multiple groups
            groups = ctx.client.get_groups_by_ids(list(group_ids))

            if not groups:
                click.echo("[WARN] No groups found", err=True)
                sys.exit(0)

            if ctx.verbose:
                click.echo(f"[INFO] Found {len(groups)} group(s)", err=True)

            # Create GroupListResponse for consistent formatting
            from prtg.models.group import GroupListResponse

            groups_response = GroupListResponse(groups=groups)
            output = ctx.formatter.format_groups(groups_response)
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
