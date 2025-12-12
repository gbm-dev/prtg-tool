"""Tests for configuration management."""

import pytest
import os
from pathlib import Path
from prtg.config import PRTGConfig, ConfigManager


class TestPRTGConfig:
    """Tests for PRTGConfig dataclass."""

    def test_valid_config(self):
        """Test creating a valid configuration."""
        config = PRTGConfig(
            url="https://prtg.example.com",
            api_token="ABC123XYZ789",
        )
        assert config.url == "https://prtg.example.com"
        assert config.api_token == "ABC123XYZ789"
        assert config.verify_ssl is True
        assert config.profile == "default"

    def test_config_with_custom_profile(self):
        """Test config with custom profile name."""
        config = PRTGConfig(
            url="https://prtg.example.com",
            api_token="ABC123",
            profile="production",
        )
        assert config.profile == "production"

    def test_config_verify_ssl_false(self):
        """Test config with SSL verification disabled."""
        config = PRTGConfig(
            url="https://prtg.example.com",
            api_token="ABC123",
            verify_ssl=False,
        )
        assert config.verify_ssl is False

    def test_url_without_scheme(self):
        """Test that URL without scheme gets https:// added."""
        config = PRTGConfig(
            url="prtg.example.com",
            api_token="ABC123",
        )
        assert config.url == "https://prtg.example.com"

    def test_url_with_http_scheme(self):
        """Test that http:// scheme is preserved."""
        config = PRTGConfig(
            url="http://prtg.example.com",
            api_token="ABC123",
        )
        assert config.url == "http://prtg.example.com"

    def test_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from URL."""
        config = PRTGConfig(
            url="https://prtg.example.com/",
            api_token="ABC123",
        )
        assert config.url == "https://prtg.example.com"

    def test_missing_url(self):
        """Test that missing URL raises ValueError."""
        with pytest.raises(ValueError, match="PRTG URL is required"):
            PRTGConfig(url="", api_token="ABC123")

    def test_missing_api_token(self):
        """Test that missing API token raises ValueError."""
        with pytest.raises(ValueError, match="API token is required"):
            PRTGConfig(url="https://prtg.example.com", api_token="")


class TestConfigManager:
    """Tests for ConfigManager."""

    def test_init_with_nonexistent_file(self):
        """Test initialization with non-existent config file."""
        manager = ConfigManager(config_path=Path("/tmp/nonexistent_config"))
        assert manager.config_path == Path("/tmp/nonexistent_config")
        assert len(manager.list_profiles()) == 0

    def test_get_config_from_args(self):
        """Test getting config from CLI arguments only."""
        manager = ConfigManager(config_path=Path("/tmp/nonexistent_config"))
        config = manager.get_config(
            url="https://prtg.example.com",
            api_token="ABC123XYZ789",
        )
        assert config.url == "https://prtg.example.com"
        assert config.api_token == "ABC123XYZ789"

    def test_get_config_from_file(self, tmp_path):
        """Test getting config from config file."""
        config_file = tmp_path / "config"
        config_file.write_text(
            "[default]\n"
            "url = https://prtg.example.com\n"
            "api_token = FILE_TOKEN_123\n"
            "verify_ssl = true\n"
        )

        manager = ConfigManager(config_path=config_file)
        config = manager.get_config()
        assert config.url == "https://prtg.example.com"
        assert config.api_token == "FILE_TOKEN_123"
        assert config.verify_ssl is True

    def test_get_config_from_profile(self, tmp_path):
        """Test getting config from specific profile."""
        config_file = tmp_path / "config"
        config_file.write_text(
            "[default]\n"
            "url = https://prtg-default.example.com\n"
            "api_token = DEFAULT_TOKEN\n"
            "\n"
            "[production]\n"
            "url = https://prtg-prod.example.com\n"
            "api_token = PROD_TOKEN\n"
            "verify_ssl = false\n"
        )

        manager = ConfigManager(config_path=config_file)
        config = manager.get_config(profile="production")
        assert config.url == "https://prtg-prod.example.com"
        assert config.api_token == "PROD_TOKEN"
        assert config.verify_ssl is False

    def test_cli_args_override_file(self, tmp_path):
        """Test that CLI args override config file values."""
        config_file = tmp_path / "config"
        config_file.write_text(
            "[default]\n"
            "url = https://prtg-file.example.com\n"
            "api_token = FILE_TOKEN\n"
        )

        manager = ConfigManager(config_path=config_file)
        config = manager.get_config(
            url="https://prtg-cli.example.com",
            api_token="CLI_TOKEN",
        )
        assert config.url == "https://prtg-cli.example.com"
        assert config.api_token == "CLI_TOKEN"

    def test_env_vars_override_file(self, tmp_path, monkeypatch):
        """Test that environment variables override config file values."""
        config_file = tmp_path / "config"
        config_file.write_text(
            "[default]\n"
            "url = https://prtg-file.example.com\n"
            "api_token = FILE_TOKEN\n"
        )

        monkeypatch.setenv("PRTG_URL", "https://prtg-env.example.com")
        monkeypatch.setenv("PRTG_API_TOKEN", "ENV_TOKEN")

        manager = ConfigManager(config_path=config_file)
        config = manager.get_config()
        assert config.url == "https://prtg-env.example.com"
        assert config.api_token == "ENV_TOKEN"

    def test_cli_args_override_env_vars(self, monkeypatch):
        """Test that CLI args override environment variables."""
        monkeypatch.setenv("PRTG_URL", "https://prtg-env.example.com")
        monkeypatch.setenv("PRTG_API_TOKEN", "ENV_TOKEN")

        manager = ConfigManager(config_path=Path("/tmp/nonexistent"))
        config = manager.get_config(
            url="https://prtg-cli.example.com",
            api_token="CLI_TOKEN",
        )
        assert config.url == "https://prtg-cli.example.com"
        assert config.api_token == "CLI_TOKEN"

    def test_api_token_rw_priority(self, monkeypatch):
        """Test that RW token has priority over RO token."""
        monkeypatch.setenv("PRTG_URL", "https://prtg.example.com")
        monkeypatch.setenv("PRTG_API_TOKEN_RO", "RO_TOKEN")
        monkeypatch.setenv("PRTG_API_TOKEN_RW", "RW_TOKEN")

        manager = ConfigManager(config_path=Path("/tmp/nonexistent"))
        config = manager.get_config()
        assert config.api_token == "RW_TOKEN"

    def test_api_token_fallback_to_ro(self, monkeypatch):
        """Test fallback to RO token when RW not available."""
        monkeypatch.setenv("PRTG_URL", "https://prtg.example.com")
        monkeypatch.setenv("PRTG_API_TOKEN_RO", "RO_TOKEN")

        manager = ConfigManager(config_path=Path("/tmp/nonexistent"))
        config = manager.get_config()
        assert config.api_token == "RO_TOKEN"

    def test_api_token_priority_over_rw(self, monkeypatch):
        """Test that PRTG_API_TOKEN has priority over RW/RO."""
        monkeypatch.setenv("PRTG_URL", "https://prtg.example.com")
        monkeypatch.setenv("PRTG_API_TOKEN", "MAIN_TOKEN")
        monkeypatch.setenv("PRTG_API_TOKEN_RW", "RW_TOKEN")
        monkeypatch.setenv("PRTG_API_TOKEN_RO", "RO_TOKEN")

        manager = ConfigManager(config_path=Path("/tmp/nonexistent"))
        config = manager.get_config()
        assert config.api_token == "MAIN_TOKEN"

    def test_no_verify_ssl_env_var(self, monkeypatch):
        """Test PRTG_NO_VERIFY_SSL environment variable."""
        monkeypatch.setenv("PRTG_URL", "https://prtg.example.com")
        monkeypatch.setenv("PRTG_API_TOKEN", "TOKEN123")
        monkeypatch.setenv("PRTG_NO_VERIFY_SSL", "1")

        manager = ConfigManager(config_path=Path("/tmp/nonexistent"))
        config = manager.get_config()
        assert config.verify_ssl is False

    def test_list_profiles(self, tmp_path):
        """Test listing available profiles."""
        config_file = tmp_path / "config"
        config_file.write_text(
            "[default]\n"
            "url = https://prtg.example.com\n"
            "\n"
            "[production]\n"
            "url = https://prtg-prod.example.com\n"
            "\n"
            "[staging]\n"
            "url = https://prtg-staging.example.com\n"
        )

        manager = ConfigManager(config_path=config_file)
        profiles = manager.list_profiles()
        assert len(profiles) == 3
        assert "default" in profiles
        assert "production" in profiles
        assert "staging" in profiles

    def test_init_config(self, tmp_path):
        """Test initializing a new config file."""
        config_file = tmp_path / "new_config"
        manager = ConfigManager(config_path=config_file)

        path = manager.init_config(config_path=config_file)
        assert path == config_file
        assert config_file.exists()

        # Verify the created config can be loaded
        manager2 = ConfigManager(config_path=config_file)
        assert "default" in manager2.list_profiles()

    def test_init_config_already_exists(self, tmp_path):
        """Test that init_config fails if file already exists."""
        config_file = tmp_path / "existing_config"
        config_file.write_text("[default]\n")

        manager = ConfigManager(config_path=config_file)
        with pytest.raises(FileExistsError):
            manager.init_config(config_path=config_file)

    def test_test_config_success(self):
        """Test successful config testing."""
        manager = ConfigManager(config_path=Path("/tmp/nonexistent"))
        success, message = manager.test_config(
            url="https://prtg.example.com",
            api_token="TOKEN123",
        )
        assert success is True
        assert "Configuration valid" in message
        assert "https://prtg.example.com" in message
        assert "TOKEN123" in message

    def test_test_config_failure(self):
        """Test config testing with invalid config."""
        manager = ConfigManager(config_path=Path("/tmp/nonexistent"))
        success, message = manager.test_config(
            url="",
            api_token="TOKEN123",
        )
        assert success is False
        assert "Configuration error" in message

    def test_profile_from_env(self, tmp_path, monkeypatch):
        """Test using profile from PRTG_PROFILE env var."""
        config_file = tmp_path / "config"
        config_file.write_text(
            "[default]\n"
            "url = https://prtg-default.example.com\n"
            "api_token = DEFAULT_TOKEN\n"
            "\n"
            "[staging]\n"
            "url = https://prtg-staging.example.com\n"
            "api_token = STAGING_TOKEN\n"
        )

        monkeypatch.setenv("PRTG_PROFILE", "staging")

        manager = ConfigManager(config_path=config_file)
        config = manager.get_config()
        assert config.profile == "staging"
        assert config.url == "https://prtg-staging.example.com"
        assert config.api_token == "STAGING_TOKEN"

    def test_dotenv_file_loading(self, tmp_path, monkeypatch):
        """Test loading configuration from .env file."""
        # Change to tmp_path so .env is found
        monkeypatch.chdir(tmp_path)

        env_file = tmp_path / ".env"
        env_file.write_text(
            "PRTG_URL=https://prtg-dotenv.example.com\n"
            "PRTG_API_TOKEN=DOTENV_TOKEN\n"
        )

        # Explicitly enable dotenv loading for this test
        manager = ConfigManager(config_path=Path("/tmp/nonexistent"), load_dotenv_file=True)
        config = manager.get_config()
        assert config.url == "https://prtg-dotenv.example.com"
        assert config.api_token == "DOTENV_TOKEN"

    def test_token_from_file_rw_priority(self, tmp_path, monkeypatch):
        """Test RW token priority in config file."""
        # Change to tmp_path to avoid loading .env from current directory
        monkeypatch.chdir(tmp_path)

        # Clear any PRTG env vars from previous tests
        monkeypatch.delenv("PRTG_API_TOKEN", raising=False)
        monkeypatch.delenv("PRTG_API_TOKEN_RW", raising=False)
        monkeypatch.delenv("PRTG_API_TOKEN_RO", raising=False)
        monkeypatch.delenv("PRTG_URL", raising=False)

        config_file = tmp_path / "config"
        config_file.write_text(
            "[default]\n"
            "url = https://prtg.example.com\n"
            "api_token_ro = RO_FILE_TOKEN\n"
            "api_token_rw = RW_FILE_TOKEN\n"
        )

        manager = ConfigManager(config_path=config_file)
        config = manager.get_config()
        assert config.api_token == "RW_FILE_TOKEN"
