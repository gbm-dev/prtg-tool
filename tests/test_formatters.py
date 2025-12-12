"""Tests for output formatters."""

import pytest
import json
from prtg.formatters.base import FormatterFactory
from prtg.formatters.json import JSONFormatter
from prtg.models.device import Device, DeviceListResponse


class TestFormatterFactory:
    """Tests for FormatterFactory."""

    def test_create_json_formatter(self):
        """Test creating JSON formatter."""
        formatter = FormatterFactory.create("json")
        assert isinstance(formatter, JSONFormatter)
        assert formatter.pretty is False

    def test_create_json_formatter_with_pretty(self):
        """Test creating JSON formatter with pretty-print."""
        formatter = FormatterFactory.create("json", pretty=True)
        assert isinstance(formatter, JSONFormatter)
        assert formatter.pretty is True

    def test_create_unknown_formatter(self):
        """Test creating unknown formatter raises error."""
        with pytest.raises(ValueError, match="Unknown formatter"):
            FormatterFactory.create("unknown")

    def test_list_formatters(self):
        """Test listing available formatters."""
        formatters = FormatterFactory.list_formatters()
        assert "json" in formatters


class TestJSONFormatter:
    """Tests for JSONFormatter."""

    def test_format_single_device(self):
        """Test formatting a single device."""
        device = Device(
            objid="2001",
            name="web-server-01",
            host="192.168.1.10",
            status="Up",
            tags=["production", "web"],
        )

        formatter = JSONFormatter()
        output = formatter.format_device(device)

        # Verify it's valid JSON
        data = json.loads(output)
        assert data["objid"] == "2001"
        assert data["name"] == "web-server-01"
        assert data["host"] == "192.168.1.10"
        assert data["status"] == "Up"
        assert data["tags"] == ["production", "web"]

    def test_format_device_exclude_none(self):
        """Test that None values are excluded from output."""
        device = Device(
            objid="2001",
            name="web-server-01",
            status="Up",
            # All other fields are None
        )

        formatter = JSONFormatter()
        output = formatter.format_device(device)

        data = json.loads(output)
        assert "objid" in data
        assert "name" in data
        assert "host" not in data  # Was None, should be excluded
        assert "location" not in data  # Was None, should be excluded

    def test_format_device_pretty(self):
        """Test formatting device with pretty-print."""
        device = Device(
            objid="2001",
            name="web-server-01",
            status="Up",
        )

        formatter = JSONFormatter(pretty=True)
        output = formatter.format_device(device)

        # Pretty-print should have newlines and indentation
        assert "\n" in output
        assert "  " in output  # Indentation

        # Should still be valid JSON
        data = json.loads(output)
        assert data["objid"] == "2001"

    def test_format_devices_list(self):
        """Test formatting a list of devices."""
        devices_list = DeviceListResponse(
            devices=[
                Device(
                    objid="2001",
                    name="web-server-01",
                    host="192.168.1.10",
                    status="Up",
                ),
                Device(
                    objid="2002",
                    name="db-server-01",
                    host="192.168.1.20",
                    status="Up",
                ),
            ]
        )

        formatter = JSONFormatter()
        output = formatter.format_devices(devices_list)

        # Should be a JSON array
        data = json.loads(output)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["objid"] == "2001"
        assert data[1]["objid"] == "2002"

    def test_format_empty_devices_list(self):
        """Test formatting an empty devices list."""
        devices_list = DeviceListResponse(devices=[])

        formatter = JSONFormatter()
        output = formatter.format_devices(devices_list)

        data = json.loads(output)
        assert data == []

    def test_format_devices_pretty(self):
        """Test formatting devices list with pretty-print."""
        devices_list = DeviceListResponse(
            devices=[
                Device(objid="2001", name="web-server-01", status="Up"),
                Device(objid="2002", name="db-server-01", status="Up"),
            ]
        )

        formatter = JSONFormatter(pretty=True)
        output = formatter.format_devices(devices_list)

        # Should have pretty formatting
        assert "\n" in output
        assert "  " in output

        # Should still be valid JSON
        data = json.loads(output)
        assert len(data) == 2

    def test_format_error(self):
        """Test formatting an error."""
        error = ValueError("Something went wrong")

        formatter = JSONFormatter()
        output = formatter.format_error(error)

        data = json.loads(output)
        assert "error" in data
        assert data["error"]["type"] == "ValueError"
        assert data["error"]["message"] == "Something went wrong"

    def test_format_error_pretty(self):
        """Test formatting error with pretty-print."""
        error = RuntimeError("Test error")

        formatter = JSONFormatter(pretty=True)
        output = formatter.format_error(error)

        # Should be pretty
        assert "\n" in output

        # Should be valid JSON
        data = json.loads(output)
        assert data["error"]["type"] == "RuntimeError"
        assert data["error"]["message"] == "Test error"

    def test_unicode_handling(self):
        """Test that Unicode characters are handled correctly."""
        device = Device(
            objid="2001",
            name="Server-日本語",  # Japanese characters
            status="Up",
            location="Zürich, Switzerland",  # German umlaut
        )

        formatter = JSONFormatter()
        output = formatter.format_device(device)

        # Should preserve Unicode
        assert "日本語" in output
        assert "Zürich" in output

        # Should be valid JSON
        data = json.loads(output)
        assert data["name"] == "Server-日本語"
        assert data["location"] == "Zürich, Switzerland"

    def test_format_device_with_all_fields(self):
        """Test formatting device with all fields populated."""
        device = Device(
            objid="2001",
            name="web-server-01",
            device="web-server-01",
            host="192.168.1.10",
            probe="Local Probe",
            group="Web Servers",
            parentid="1000",
            status="Up",
            status_raw="3",
            message="OK",
            tags=["production", "web", "linux"],
            priority="3",
            location="Rack 4",
            comments="Main web server",
            upsens="10",
            downsens="0",
            sensor_count_up=10,
            sensor_count_down=0,
        )

        formatter = JSONFormatter()
        output = formatter.format_device(device)

        data = json.loads(output)
        assert data["objid"] == "2001"
        assert data["name"] == "web-server-01"
        assert data["host"] == "192.168.1.10"
        assert data["tags"] == ["production", "web", "linux"]
        assert data["sensor_count_up"] == 10
