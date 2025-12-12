"""Configuration management for PRTG CLI Tool."""

import os
from pathlib import Path
from configparser import ConfigParser
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class PRTGConfig:
    """Configuration for PRTG connection."""

    url: str
    api_token: str
    verify_ssl: bool = True
    profile: str = "default"

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.url:
            raise ValueError("PRTG URL is required")
        if not self.api_token:
            raise ValueError("API token is required")

        # Ensure URL doesn't have trailing slash
        self.url = self.url.rstrip("/")

        # Ensure URL has scheme
        if not self.url.startswith(("http://", "https://")):
            self.url = f"https://{self.url}"


class ConfigManager:
    """Manage PRTG CLI configuration from files, env vars, and CLI args."""

    DEFAULT_CONFIG_PATH = Path.home() / ".config" / "prtg" / "config"
    ENV_PREFIX = "PRTG_"

    def __init__(self, config_path: Optional[Path] = None, load_dotenv_file: Optional[bool] = None):
        """Initialize configuration manager.

        Args:
            config_path: Path to config file (default: ~/.config/prtg/config)
            load_dotenv_file: Whether to load .env file from current directory.
                             None (default): auto-detect (skip in pytest, load otherwise)
                             True: always load
                             False: never load
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.parser = ConfigParser()

        # Load .env file from current directory first (highest priority for env vars)
        # Auto-detect: skip .env in test environments unless explicitly requested
        should_load = load_dotenv_file
        if load_dotenv_file is None:
            # Auto-detect: don't load in pytest to avoid test pollution
            should_load = "PYTEST_CURRENT_TEST" not in os.environ

        if should_load:
            env_path = Path.cwd() / ".env"
            if env_path.exists():
                load_dotenv(dotenv_path=env_path, override=True)

        # Load config file if it exists
        if self.config_path.exists():
            self.parser.read(self.config_path)

    def get_config(
        self,
        profile: Optional[str] = None,
        url: Optional[str] = None,
        api_token: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
    ) -> PRTGConfig:
        """Get configuration with precedence: CLI args > env vars > .env > config file.

        Args:
            profile: Profile name to use from config file
            url: PRTG server URL (overrides config file)
            api_token: API token (overrides config file)
            verify_ssl: SSL verification flag (overrides config file)

        Returns:
            PRTGConfig instance

        Raises:
            ValueError: If required configuration is missing
        """
        # Determine which profile to use
        profile = profile or self._get_env("PROFILE") or "default"

        # Get config values with precedence: CLI > env > file
        config_url = (
            url
            or self._get_env("URL")
            or self._get_from_file(profile, "url")
        )

        # API token with RW/RO support
        # Priority: CLI arg > PRTG_API_TOKEN > PRTG_API_TOKEN_RW > PRTG_API_TOKEN_RO > config file
        config_api_token = (
            api_token
            or self._get_env("API_TOKEN")
            or self._get_env("API_TOKEN_RW")
            or self._get_env("API_TOKEN_RO")
            or self._get_from_file(profile, "api_token")
            or self._get_from_file(profile, "api_token_rw")
            or self._get_from_file(profile, "api_token_ro")
        )

        # Handle verify_ssl - needs special handling for boolean
        if verify_ssl is not None:
            config_verify_ssl = verify_ssl
        else:
            env_verify = self._get_env("NO_VERIFY_SSL")
            if env_verify:
                config_verify_ssl = env_verify.lower() not in ("1", "true", "yes")
            else:
                file_verify = self._get_from_file(profile, "verify_ssl")
                if file_verify:
                    config_verify_ssl = file_verify.lower() in ("true", "yes", "1")
                else:
                    config_verify_ssl = True

        return PRTGConfig(
            url=config_url or "",
            api_token=config_api_token or "",
            verify_ssl=config_verify_ssl,
            profile=profile,
        )

    def _get_env(self, key: str) -> Optional[str]:
        """Get value from environment variable.

        Args:
            key: Environment variable key (without PRTG_ prefix)

        Returns:
            Environment variable value or None
        """
        return os.environ.get(f"{self.ENV_PREFIX}{key}")

    def _get_from_file(self, profile: str, key: str) -> Optional[str]:
        """Get value from config file.

        Args:
            profile: Profile name
            key: Configuration key

        Returns:
            Configuration value or None
        """
        if not self.parser.has_section(profile):
            return None
        return self.parser.get(profile, key, fallback=None)

    def list_profiles(self) -> list[str]:
        """List all available profiles in the config file.

        Returns:
            List of profile names
        """
        return self.parser.sections()

    def init_config(self, config_path: Optional[Path] = None) -> Path:
        """Create a default configuration file.

        Args:
            config_path: Path to create config file (default: ~/.config/prtg/config)

        Returns:
            Path to created config file

        Raises:
            FileExistsError: If config file already exists
        """
        path = config_path or self.DEFAULT_CONFIG_PATH

        if path.exists():
            raise FileExistsError(f"Config file already exists: {path}")

        # Create parent directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        # Create default config
        parser = ConfigParser()
        parser["default"] = {
            "url": "https://prtg.example.com",
            "api_token": "YOUR_API_TOKEN_HERE",
            "verify_ssl": "true",
        }

        with open(path, "w") as f:
            f.write("# PRTG CLI Tool Configuration\n")
            f.write("# Get your API token from: Setup > My Account > API Keys\n")
            f.write("# Create additional sections for different profiles\n\n")
            parser.write(f)

        return path

    def test_config(
        self,
        profile: Optional[str] = None,
        url: Optional[str] = None,
        api_token: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
    ) -> tuple[bool, str]:
        """Test configuration by attempting to retrieve it.

        Args:
            profile: Profile name to test
            url: PRTG server URL (overrides config file)
            api_token: API token (overrides config file)
            verify_ssl: SSL verification flag (overrides config file)

        Returns:
            Tuple of (success, message)
        """
        try:
            config = self.get_config(
                profile=profile,
                url=url,
                api_token=api_token,
                verify_ssl=verify_ssl,
            )
            return (
                True,
                f"Configuration valid:\n"
                f"  Profile: {config.profile}\n"
                f"  URL: {config.url}\n"
                f"  API Token: {config.api_token[:10]}...{config.api_token[-10:] if len(config.api_token) > 20 else ''}\n"
                f"  Verify SSL: {config.verify_ssl}",
            )
        except ValueError as e:
            return (False, f"Configuration error: {e}")
