"""Main CLI entry point for PRTG Tool."""

import sys
import click
from pathlib import Path

from prtg.config import ConfigManager, PRTGConfig
from prtg.client import PRTGClient, PRTGClientError
from prtg.formatters.base import FormatterFactory
import prtg.formatters.json  # Import to register formatter
from prtg.commands import device, group, sensor


# Click context object to pass config and client
class Context:
    """CLI context object."""

    def __init__(self):
        self.config: PRTGConfig = None
        self.client: PRTGClient = None
        self.formatter = None
        self.verbose = False
        self.debug = False
        self.cli_options = {}

    def init_client(self):
        """Initialize the PRTG client (lazy initialization)."""
        if self.client is not None:
            return  # Already initialized

        # Create config manager
        config_manager = ConfigManager(config_path=self.cli_options.get("config"))

        try:
            # Get configuration with precedence: CLI args > env vars > config file
            self.config = config_manager.get_config(
                profile=self.cli_options.get("profile"),
                url=self.cli_options.get("url"),
                api_token=self.cli_options.get("api_token"),
                verify_ssl=False if self.cli_options.get("no_verify_ssl") else None,
            )

            if self.verbose:
                click.echo(f"[INFO] Using profile: {self.config.profile}", err=True)
                click.echo(f"[INFO] Server URL: {self.config.url}", err=True)
                if self.cli_options.get("no_verify_ssl"):
                    click.echo("[WARN] SSL verification disabled", err=True)

            # Create API client
            self.client = PRTGClient(self.config)

            # Create formatter
            self.formatter = FormatterFactory.create(
                self.cli_options.get("output", "json"),
                pretty=self.cli_options.get("pretty", True),
            )

        except ValueError as e:
            click.echo(f"[ERROR] Configuration error: {e}", err=True)
            click.echo(
                "\nRun 'prtg config init' to create a config file, "
                "or provide --url and --api-token options.",
                err=True,
            )
            sys.exit(1)


pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group()
@click.option(
    "--url",
    envvar="PRTG_URL",
    help="PRTG server URL",
)
@click.option(
    "--api-token",
    envvar="PRTG_API_TOKEN",
    help="API authentication token",
)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    envvar="PRTG_CONFIG",
    help="Config file path",
)
@click.option(
    "--profile",
    envvar="PRTG_PROFILE",
    help="Profile name from config file",
)
@click.option(
    "--no-verify-ssl",
    is_flag=True,
    envvar="PRTG_NO_VERIFY_SSL",
    help="Disable SSL verification",
)
@click.option(
    "--output",
    type=click.Choice(["json"]),
    default="json",
    envvar="PRTG_OUTPUT_FORMAT",
    help="Output format",
)
@click.option(
    "--pretty/--no-pretty",
    default=True,
    help="Pretty-print JSON output (default: enabled)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output (to stderr)",
)
@click.option(
    "--debug",
    is_flag=True,
    envvar="PRTG_DEBUG",
    help="Debug mode (show API calls)",
)
@pass_context
def cli(
    ctx: Context,
    url,
    api_token,
    config,
    profile,
    no_verify_ssl,
    output,
    pretty,
    verbose,
    debug,
):
    """PRTG CLI Tool - Command-line interface for PRTG Network Monitor."""
    ctx.verbose = verbose
    ctx.debug = debug

    # Store CLI options in context for lazy initialization
    ctx.cli_options = {
        "url": url,
        "api_token": api_token,
        "config": config,
        "profile": profile,
        "no_verify_ssl": no_verify_ssl,
        "output": output,
        "pretty": pretty,
    }


# Add command groups
cli.add_command(device.device)
cli.add_command(group.group)
cli.add_command(sensor.sensor)


if __name__ == "__main__":
    cli()
