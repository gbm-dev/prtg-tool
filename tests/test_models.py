"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from prtg.models.device import Device, DeviceListResponse


class TestDevice:
    """Tests for Device model."""

    def test_basic_device_creation(self):
        """Test creating a basic device with minimal fields."""
        device = Device(
            objid="2001",
            name="test-device",
            status="Up",
        )
        assert device.objid == "2001"
        assert device.name == "test-device"
        assert device.status == "Up"
        assert device.tags == []

    def test_device_with_all_fields(self):
        """Test creating a device with all fields populated."""
        device = Device(
            objid="2001",
            name="web-server-01",
            device="web-server-01",
            host="192.168.1.10",
            probe="Local Probe",
            group="Web Servers",
            status="Up",
            status_raw="3",
            message="OK",
            tags=["production", "web", "linux"],
            priority="3",
            location="Rack 4",
            comments="Main web server",
            upsens="10",
            downsens="0",
            warnsens="0",
        )
        assert device.objid == "2001"
        assert device.host == "192.168.1.10"
        assert device.tags == ["production", "web", "linux"]
        assert device.upsens == "10"

    def test_tags_from_string(self):
        """Test that tags are parsed from space-separated string."""
        device = Device(
            objid="2001",
            name="test-device",
            status="Up",
            tags="production web linux",
        )
        assert device.tags == ["production", "web", "linux"]

    def test_tags_empty_string(self):
        """Test that empty string tags become empty list."""
        device = Device(
            objid="2001",
            name="test-device",
            status="Up",
            tags="",
        )
        assert device.tags == []

    def test_tags_with_extra_spaces(self):
        """Test that tags with extra spaces are cleaned up."""
        device = Device(
            objid="2001",
            name="test-device",
            status="Up",
            tags="  production   web   linux  ",
        )
        assert device.tags == ["production", "web", "linux"]

    def test_tags_from_list(self):
        """Test that tags can be provided as list."""
        device = Device(
            objid="2001",
            name="test-device",
            status="Up",
            tags=["production", "web"],
        )
        assert device.tags == ["production", "web"]

    def test_sensor_count_conversion(self):
        """Test that sensor counts are converted to integers."""
        device = Device(
            objid="2001",
            name="test-device",
            status="Up",
            upsens="10",
            downsens="2",
            warnsens="1",
            pausedsens="3",
            unusualsens="0",
        )
        assert device.sensor_count_up == 10
        assert device.sensor_count_down == 2
        assert device.sensor_count_warning == 1
        assert device.sensor_count_paused == 3
        assert device.sensor_count_unusual == 0

    def test_sensor_count_with_integers(self):
        """Test that integer sensor counts are converted to strings."""
        device = Device(
            objid="2001",
            name="test-device",
            status="Up",
            upsens=10,
            downsens=2,
        )
        assert device.upsens == "10"
        assert device.downsens == "2"
        assert device.sensor_count_up == 10
        assert device.sensor_count_down == 2

    def test_sensor_count_invalid(self):
        """Test that invalid sensor counts don't break the model."""
        device = Device(
            objid="2001",
            name="test-device",
            status="Up",
            upsens="invalid",
        )
        # Should not raise an error, just not set the int field
        assert device.upsens == "invalid"
        assert device.sensor_count_up is None

    def test_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError) as exc_info:
            Device()

        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}
        assert "objid" in error_fields
        assert "name" in error_fields
        assert "status" in error_fields

    def test_extra_fields_ignored(self):
        """Test that extra fields from API are ignored."""
        device = Device(
            objid="2001",
            name="test-device",
            status="Up",
            unknown_field="should be ignored",
            another_unknown="also ignored",
        )
        assert device.objid == "2001"
        assert not hasattr(device, "unknown_field")

    def test_whitespace_stripped(self):
        """Test that whitespace is stripped from string fields."""
        device = Device(
            objid="  2001  ",
            name="  test-device  ",
            status="  Up  ",
        )
        assert device.objid == "2001"
        assert device.name == "test-device"
        assert device.status == "Up"


class TestDeviceListResponse:
    """Tests for DeviceListResponse model."""

    def test_empty_device_list(self):
        """Test creating an empty device list response."""
        response = DeviceListResponse()
        assert response.devices == []
        assert response.total == 0

    def test_device_list_with_devices(self):
        """Test creating a device list response with devices."""
        response = DeviceListResponse(
            devices=[
                Device(objid="2001", name="device-1", status="Up"),
                Device(objid="2002", name="device-2", status="Down"),
            ]
        )
        assert len(response.devices) == 2
        assert response.total == 2
        assert response.devices[0].objid == "2001"
        assert response.devices[1].objid == "2002"

    def test_device_list_with_metadata(self):
        """Test device list response with PRTG metadata."""
        response = DeviceListResponse(
            prtg_version="21.4.73",
            treesize=150,
            devices=[
                Device(objid="2001", name="device-1", status="Up"),
            ],
        )
        assert response.prtg_version == "21.4.73"
        assert response.treesize == 150
        assert response.total == 1

    def test_device_list_from_api_response(self):
        """Test parsing a realistic API response."""
        api_response = {
            "prtg-version": "21.4.73.1234",
            "treesize": 250,
            "devices": [
                {
                    "objid": "2001",
                    "name": "Server-01",
                    "device": "Server-01",
                    "host": "192.168.1.100",
                    "probe": "Local Probe",
                    "group": "Network Devices",
                    "status": "Up",
                    "message": "OK",
                    "tags": "production server",
                    "upsens": "10",
                    "downsens": "0",
                },
                {
                    "objid": "2002",
                    "name": "Server-02",
                    "device": "Server-02",
                    "host": "192.168.1.101",
                    "probe": "Local Probe",
                    "group": "Network Devices",
                    "status": "Down",
                    "message": "Host unreachable",
                    "tags": "production server",
                    "upsens": "8",
                    "downsens": "2",
                },
            ],
        }
        response = DeviceListResponse(**api_response)
        assert response.prtg_version == "21.4.73.1234"
        assert response.treesize == 250
        assert response.total == 2
        assert response.devices[0].host == "192.168.1.100"
        assert response.devices[0].tags == ["production", "server"]
        assert response.devices[1].status == "Down"
        assert response.devices[1].sensor_count_up == 8
