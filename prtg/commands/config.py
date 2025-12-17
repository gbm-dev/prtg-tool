"""Config commands for PRTG CLI."""

import sys
import click
from pathlib import Path
from prtg.config import ConfigManager


@click.group(name="config")
def config():
    """Manage PRTG CLI configuration."""
    pass


@config.command(name="init")
@click.option(
    "--path",
    type=click.Path(path_type=Path),
    help="Config file path (default: ~/.config/prtg/config)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing config file",
)
def config_init(path, force):
    """Create a default configuration file.

    Creates a config file with example values at ~/.config/prtg/config
    (or a custom path if specified). Edit this file to add your PRTG
    server URL and API token.

    Examples:
        prtg config init
        prtg config init --path ./my-config
        prtg config init --force  # Overwrite existing file
    """
    config_manager = ConfigManager()
    target_path = path or config_manager.DEFAULT_CONFIG_PATH

    # Check if file exists and handle force flag
    if target_path.exists() and not force:
        click.echo(
            f"[ERROR] Config file already exists: {target_path}\n"
            f"Use --force to overwrite, or edit the existing file.",
            err=True,
        )
        sys.exit(1)

    # Remove existing file if force is set
    if target_path.exists() and force:
        target_path.unlink()

    try:
        created_path = config_manager.init_config(target_path)
        click.echo(f"[SUCCESS] Created config file: {created_path}")
        click.echo(f"\nNext steps:")
        click.echo(f"  1. Edit the config file: {created_path}")
        click.echo(f"  2. Update the 'url' and 'api_token' values")
        click.echo(f"  3. Get your API token from: Setup > My Account > API Keys")
        click.echo(f"  4. Test your config: prtg config test")
    except Exception as e:
        click.echo(f"[ERROR] Failed to create config file: {e}", err=True)
        sys.exit(1)


@config.command(name="list")
@click.option(
    "--path",
    type=click.Path(exists=True, path_type=Path),
    help="Config file path (default: ~/.config/prtg/config)",
)
def config_list(path):
    """List all profiles in the configuration file.

    Shows all profile sections defined in your config file.
    Use the --profile option with other commands to select
    a specific profile.

    Examples:
        prtg config list
        prtg config list --path ./my-config
    """
    config_manager = ConfigManager(config_path=path)

    if not config_manager.config_path.exists():
        click.echo(
            f"[ERROR] Config file not found: {config_manager.config_path}\n"
            f"Run 'prtg config init' to create it.",
            err=True,
        )
        sys.exit(1)

    profiles = config_manager.list_profiles()

    if not profiles:
        click.echo(f"[INFO] No profiles found in: {config_manager.config_path}")
        return

    click.echo(f"Profiles in {config_manager.config_path}:")
    for profile in profiles:
        click.echo(f"  - {profile}")


@config.command(name="test")
@click.option(
    "--path",
    type=click.Path(exists=True, path_type=Path),
    help="Config file path (default: ~/.config/prtg/config)",
)
@click.option(
    "--profile",
    help="Profile name to test (default: default)",
)
@click.option(
    "--url",
    help="PRTG server URL (overrides config file)",
)
@click.option(
    "--api-token",
    help="API token (overrides config file)",
)
def config_test(path, profile, url, api_token):
    """Test configuration by loading and validating it.

    Validates that the configuration can be loaded and contains
    required values. This does NOT test the connection to PRTG.

    Examples:
        prtg config test
        prtg config test --profile production
        prtg config test --url https://prtg.example.com --api-token TOKEN
    """
    config_manager = ConfigManager(config_path=path)

    success, message = config_manager.test_config(
        profile=profile,
        url=url,
        api_token=api_token,
    )

    if success:
        click.echo(f"[SUCCESS] {message}")
    else:
        click.echo(f"[ERROR] {message}", err=True)
        sys.exit(1)


@config.command(name="show")
@click.option(
    "--path",
    type=click.Path(exists=True, path_type=Path),
    help="Config file path (default: ~/.config/prtg/config)",
)
def config_show(path):
    """Show the path to the configuration file.

    Displays the location of the config file being used.
    Useful for finding where your config is stored.

    Examples:
        prtg config show
        prtg config show --path ./my-config
    """
    config_manager = ConfigManager(config_path=path)

    click.echo(f"Config file path: {config_manager.config_path}")

    if config_manager.config_path.exists():
        click.echo(f"Status: ✓ exists")

        # Show file size and modification time
        stat = config_manager.config_path.stat()
        click.echo(f"Size: {stat.st_size} bytes")

        from datetime import datetime
        mtime = datetime.fromtimestamp(stat.st_mtime)
        click.echo(f"Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        click.echo(f"Status: ✗ does not exist")
        click.echo(f"\nRun 'prtg config init' to create it.")
