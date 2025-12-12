"""Tests for Sensor models and commands."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch
from pydantic import ValidationError

from prtg.models.sensor import Sensor, SensorListResponse
from prtg.client import PRTGClient, PRTGNotFoundError
from prtg.config import PRTGConfig


# Load fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(filename: str) -> dict:
    """Load a JSON fixture file."""
    with open(FIXTURES_DIR / filename) as f:
        return json.load(f)


class TestSensorModel:
    """Tests for Sensor Pydantic model."""

    def test_basic_sensor_creation(self):
        """Test creating a basic sensor with minimal fields."""
        sensor = Sensor(
            objid="2460",
            name="Ping",
            status="Up",
        )
        assert sensor.objid == "2460"
        assert sensor.name == "Ping"
        assert sensor.status == "Up"
        assert sensor.tags == []

    def test_sensor_with_all_fields(self):
        """Test creating a sensor with all fields populated."""
        sensor = Sensor(
            objid="2460",
            name="Ping",
            sensor="Ping",
            device="web-server-01",
            group="Web Servers",
            probe="Local Probe",
            parentid="2001",
            status="Up",
            status_raw="3",
            message="OK",
            sensor_type="Ping",
            interval="60 s",
            lastvalue="5 ms",
            lastmessage="OK",
            downtime="0 %",
            uptime="100 %",
            priority="3",
            tags=["pingsensor", "production"],
        )
        assert sensor.objid == "2460"
        assert sensor.device == "web-server-01"
        assert sensor.parentid == "2001"
        assert sensor.sensor_type == "Ping"
        assert sensor.lastvalue == "5 ms"
        assert sensor.tags == ["pingsensor", "production"]

    def test_sensor_objid_conversion(self):
        """Test that numeric objid is converted to string."""
        sensor = Sensor(
            objid=2460,
            name="Ping",
            status="Up",
        )
        assert sensor.objid == "2460"
        assert isinstance(sensor.objid, str)

    def test_sensor_parentid_conversion(self):
        """Test that numeric parentid is converted to string."""
        sensor = Sensor(
            objid="2460",
            name="Ping",
            status="Up",
            parentid=2001,
        )
        assert sensor.parentid == "2001"
        assert isinstance(sensor.parentid, str)

    def test_tags_from_string(self):
        """Test that tags are parsed from space-separated string."""
        sensor = Sensor(
            objid="2460",
            name="Ping",
            status="Up",
            tags="pingsensor production monitoring",
        )
        assert sensor.tags == ["pingsensor", "production", "monitoring"]

    def test_tags_empty_string(self):
        """Test that empty string tags become empty list."""
        sensor = Sensor(
            objid="2460",
            name="Ping",
            status="Up",
            tags="",
        )
        assert sensor.tags == []

    def test_tags_with_extra_spaces(self):
        """Test that tags with extra spaces are cleaned up."""
        sensor = Sensor(
            objid="2460",
            name="Ping",
            status="Up",
            tags="  pingsensor   production  ",
        )
        assert sensor.tags == ["pingsensor", "production"]

    def test_tags_from_list(self):
        """Test that tags can be provided as list."""
        sensor = Sensor(
            objid="2460",
            name="Ping",
            status="Up",
            tags=["pingsensor", "production"],
        )
        assert sensor.tags == ["pingsensor", "production"]

    def test_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError) as exc_info:
            Sensor()

        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}
        assert "objid" in error_fields
        assert "name" in error_fields
        assert "status" in error_fields

    def test_extra_fields_ignored(self):
        """Test that extra fields from API are ignored."""
        sensor = Sensor(
            objid="2460",
            name="Ping",
            status="Up",
            unknown_field="should be ignored",
            another_unknown="also ignored",
        )
        assert sensor.objid == "2460"
        assert not hasattr(sensor, "unknown_field")

    def test_whitespace_stripped(self):
        """Test that whitespace is stripped from string fields."""
        sensor = Sensor(
            objid="  2460  ",
            name="  Ping  ",
            status="  Up  ",
        )
        assert sensor.objid == "2460"
        assert sensor.name == "Ping"
        assert sensor.status == "Up"

    def test_optional_fields_none(self):
        """Test that optional fields can be None."""
        sensor = Sensor(
            objid="2460",
            name="Ping",
            status="Up",
            device=None,
            parentid=None,
            lastvalue=None,
        )
        assert sensor.objid == "2460"
        assert sensor.device is None
        assert sensor.parentid is None
        assert sensor.lastvalue is None


class TestSensorListResponse:
    """Tests for SensorListResponse model."""

    def test_empty_sensor_list(self):
        """Test creating an empty sensor list response."""
        response = SensorListResponse()
        assert response.sensors == []
        assert response.total == 0

    def test_sensor_list_with_sensors(self):
        """Test creating a sensor list response with sensors."""
        response = SensorListResponse(
            sensors=[
                Sensor(objid="2460", name="Ping", status="Up"),
                Sensor(objid="2461", name="HTTP", status="Up"),
                Sensor(objid="2462", name="Disk Free", status="Warning"),
            ]
        )
        assert len(response.sensors) == 3
        assert response.total == 3
        assert response.sensors[0].objid == "2460"
        assert response.sensors[1].objid == "2461"
        assert response.sensors[2].status == "Warning"

    def test_sensor_list_with_metadata(self):
        """Test sensor list response with PRTG metadata."""
        response = SensorListResponse(
            prtg_version="24.3.100.1361",
            treesize=150,
            sensors=[
                Sensor(objid="2460", name="Ping", status="Up"),
            ],
        )
        assert response.prtg_version == "24.3.100.1361"
        assert response.treesize == 150
        assert response.total == 1

    def test_sensor_list_from_fixture(self):
        """Test parsing the sensors fixture file."""
        fixture_data = load_fixture("sensors.json")
        response = SensorListResponse(**fixture_data)

        assert response.prtg_version == "24.3.100.1361"
        assert response.treesize == 150
        assert response.total == 6

        # Test first sensor
        sensor1 = response.sensors[0]
        assert sensor1.objid == "2460"
        assert sensor1.name == "Ping"
        assert sensor1.device == "web-server-01"
        assert sensor1.status == "Up"
        assert sensor1.sensor_type == "Ping"
        assert sensor1.lastvalue == "5 ms"
        assert sensor1.tags == ["pingsensor", "production"]

        # Test sensor with warning status
        sensor3 = response.sensors[2]
        assert sensor3.objid == "2462"
        assert sensor3.status == "Warning"
        assert sensor3.message == "Low disk space"

        # Test sensor with down status
        sensor5 = response.sensors[4]
        assert sensor5.objid == "2480"
        assert sensor5.status == "Down"
        assert sensor5.message == "Sensor timeout"

    def test_sensor_list_from_api_response(self):
        """Test parsing a realistic API response."""
        api_response = {
            "prtg-version": "24.3.100.1361",
            "treesize": 50,
            "sensors": [
                {
                    "objid": "2460",
                    "name": "Ping",
                    "sensor": "Ping",
                    "device": "web-server-01",
                    "group": "Web Servers",
                    "probe": "Local Probe",
                    "parentid": "2001",
                    "status": "Up",
                    "status_raw": "3",
                    "message": "OK",
                    "sensor_type": "Ping",
                    "interval": "60 s",
                    "lastvalue": "5 ms",
                    "tags": "pingsensor production",
                },
                {
                    "objid": "2480",
                    "name": "CPU Load",
                    "sensor": "CPU Load",
                    "device": "app-server-01",
                    "group": "Application Servers",
                    "status": "Down",
                    "status_raw": "5",
                    "message": "Sensor timeout",
                    "sensor_type": "SNMP CPU Load",
                    "tags": "cpu snmp",
                },
            ],
        }
        response = SensorListResponse(**api_response)

        assert response.prtg_version == "24.3.100.1361"
        assert response.treesize == 50
        assert response.total == 2
        assert response.sensors[0].name == "Ping"
        assert response.sensors[0].tags == ["pingsensor", "production"]
        assert response.sensors[1].status == "Down"
        assert response.sensors[1].tags == ["cpu", "snmp"]


@pytest.fixture
def config():
    """Create a test PRTG configuration."""
    return PRTGConfig(
        url="https://prtg.example.com",
        api_token="ABC123XYZ789TOKEN",
        verify_ssl=True,
    )


@pytest.fixture
def client(config):
    """Create a test PRTG client."""
    return PRTGClient(config)


class TestPRTGClientSensors:
    """Tests for PRTG client sensor methods."""

    @patch("requests.Session.request")
    def test_get_sensors(self, mock_request, client):
        """Test getting list of sensors."""
        fixture_data = load_fixture("sensors.json")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture_data
        mock_request.return_value = mock_response

        result = client.get_sensors()

        assert result.total == 6
        assert len(result.sensors) == 6
        assert result.sensors[0].objid == "2460"
        assert result.sensors[0].name == "Ping"
        assert result.sensors[0].device == "web-server-01"

        # Verify API was called correctly
        call_kwargs = mock_request.call_args[1]
        assert "content" in call_kwargs["params"]
        assert call_kwargs["params"]["content"] == "sensors"

    @patch("requests.Session.request")
    def test_get_sensors_with_filters(self, mock_request, client):
        """Test getting sensors with status filter."""
        fixture_data = load_fixture("sensors.json")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture_data
        mock_request.return_value = mock_response

        result = client.get_sensors(filter_status="Up")

        # Verify API was called with filter (status is converted to raw code)
        call_kwargs = mock_request.call_args[1]
        assert "filter_status" in call_kwargs["params"]
        assert call_kwargs["params"]["filter_status"] == "3"  # "Up" maps to "3"

    @patch("requests.Session.request")
    def test_get_sensors_with_tags(self, mock_request, client):
        """Test getting sensors with tag filter."""
        fixture_data = load_fixture("sensors.json")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture_data
        mock_request.return_value = mock_response

        result = client.get_sensors(filter_tags="production")

        # Verify API was called with tag filter
        call_kwargs = mock_request.call_args[1]
        assert "filter_tags" in call_kwargs["params"]

    @patch("requests.Session.request")
    def test_get_sensors_with_pagination(self, mock_request, client):
        """Test getting sensors with pagination."""
        fixture_data = load_fixture("sensors.json")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture_data
        mock_request.return_value = mock_response

        result = client.get_sensors(count=10, start=0)

        # Verify API was called with pagination params
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["params"]["count"] == 10
        assert call_kwargs["params"]["start"] == 0

    @patch("requests.Session.request")
    def test_get_sensors_custom_columns(self, mock_request, client):
        """Test getting sensors with custom columns."""
        fixture_data = load_fixture("sensors.json")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture_data
        mock_request.return_value = mock_response

        custom_columns = ["objid", "name", "status", "lastvalue"]
        result = client.get_sensors(columns=custom_columns)

        # Verify custom columns were used
        call_kwargs = mock_request.call_args[1]
        assert "columns" in call_kwargs["params"]
        assert "objid" in call_kwargs["params"]["columns"]

    @patch("requests.Session.request")
    def test_get_sensor(self, mock_request, client):
        """Test getting a single sensor by ID."""
        fixture_data = load_fixture("sensors.json")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture_data
        mock_request.return_value = mock_response

        result = client.get_sensor("2460")

        assert result.objid == "2460"
        assert result.name == "Ping"
        assert result.device == "web-server-01"

        # Verify API was called with filter_objid
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["params"]["filter_objid"] == "2460"

    @patch("requests.Session.request")
    def test_get_sensor_not_found(self, mock_request, client):
        """Test getting a sensor that doesn't exist."""
        # Return empty sensor list
        empty_response = {"sensors": []}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = empty_response
        mock_request.return_value = mock_response

        with pytest.raises(PRTGNotFoundError, match="Sensor not found: 9999"):
            client.get_sensor("9999")

    @patch("requests.Session.request")
    def test_get_sensors_by_ids(self, mock_request, client):
        """Test getting multiple sensors by IDs."""
        fixture_data = load_fixture("sensors.json")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture_data
        mock_request.return_value = mock_response

        sensor_ids = ["2460", "2461", "2462"]
        result = client.get_sensors_by_ids(sensor_ids)

        assert len(result) == 3  # One sensor per requested ID
        # Each call to get_sensor returns one sensor


class TestPRTGClientSensorHistoricData:
    """Tests for PRTG client sensor historic data methods."""

    @patch("requests.Session.request")
    def test_get_sensor_historicdata_csv(self, mock_request, client):
        """Test getting sensor historic data in CSV format."""
        # Load CSV fixture
        fixture_path = FIXTURES_DIR / "sensor_historicdata.csv"
        with open(fixture_path) as f:
            csv_data = f.read()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = csv_data
        mock_response.content = csv_data.encode()
        mock_request.return_value = mock_response

        result = client.get_sensor_historicdata(
            sensor_id="2460",
            start_date="2024-01-15-00-00-00",
            end_date="2024-01-15-01-00-00",
            avg_interval=0,
            output_format="csv"
        )

        assert isinstance(result, str)
        assert "Date Time,Ping Time" in result
        assert "2024-01-15 00:00:00" in result

        # Verify API was called correctly
        call_kwargs = mock_request.call_args[1]
        assert "historicdata.csv" in call_kwargs["url"]
        assert call_kwargs["params"]["id"] == "2460"
        assert call_kwargs["params"]["sdate"] == "2024-01-15-00-00-00"
        assert call_kwargs["params"]["edate"] == "2024-01-15-01-00-00"
        assert call_kwargs["params"]["avg"] == 0

    @patch("requests.Session.request")
    def test_get_sensor_historicdata_json(self, mock_request, client):
        """Test getting sensor historic data in JSON format."""
        fixture_data = load_fixture("sensor_historicdata.json")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture_data
        mock_request.return_value = mock_response

        result = client.get_sensor_historicdata(
            sensor_id="2460",
            start_date="2024-01-15-00-00-00",
            end_date="2024-01-15-01-00-00",
            avg_interval=0,
            output_format="json"
        )

        assert isinstance(result, dict)
        assert "histdata" in result
        assert len(result["histdata"]) == 10
        assert result["sensorid"] == "2460"

        # Verify API was called correctly
        call_kwargs = mock_request.call_args[1]
        assert "historicdata.json" in call_kwargs["url"]

    @patch("requests.Session.request")
    def test_get_sensor_historicdata_with_averaging(self, mock_request, client):
        """Test getting sensor historic data with averaging interval."""
        fixture_path = FIXTURES_DIR / "sensor_historicdata.csv"
        with open(fixture_path) as f:
            csv_data = f.read()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = csv_data
        mock_response.content = csv_data.encode()
        mock_request.return_value = mock_response

        # Test hourly averaging
        result = client.get_sensor_historicdata(
            sensor_id="2460",
            start_date="2024-01-01-00-00-00",
            end_date="2024-01-31-23-59-59",
            avg_interval=3600,  # 1 hour
            output_format="csv"
        )

        assert isinstance(result, str)
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["params"]["avg"] == 3600

    @patch("requests.Session.request")
    def test_get_sensor_historicdata_rate_limit_error(self, mock_request, client):
        """Test handling of rate limit error (429)."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_request.return_value = mock_response

        from prtg.client import PRTGAPIError

        with pytest.raises(PRTGAPIError, match="Rate limit exceeded.*5.*minute"):
            client.get_sensor_historicdata(
                sensor_id="2460",
                start_date="2024-01-15-00-00-00",
                end_date="2024-01-15-01-00-00",
                avg_interval=0,
                output_format="csv"
            )
