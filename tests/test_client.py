"""Tests for PRTG API client."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch
import requests

from prtg.client import (
    PRTGClient,
    PRTGClientError,
    PRTGAuthenticationError,
    PRTGNotFoundError,
    PRTGAPIError,
)
from prtg.config import PRTGConfig


# Load fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(filename: str) -> dict:
    """Load a JSON fixture file."""
    with open(FIXTURES_DIR / filename) as f:
        return json.load(f)


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


class TestPRTGClient:
    """Tests for PRTGClient."""

    def test_init(self, config):
        """Test client initialization."""
        client = PRTGClient(config)
        assert client.config == config
        assert client.base_url == "https://prtg.example.com/api"
        assert client.session is not None

    def test_build_auth_params(self, client):
        """Test building authentication parameters."""
        params = client._build_auth_params()
        assert params["apitoken"] == "ABC123XYZ789TOKEN"

    @patch("requests.Session.request")
    def test_request_success(self, mock_request, client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_request.return_value = mock_response

        result = client._request("test.json", params={"key": "value"})

        assert result == {"test": "data"}
        mock_request.assert_called_once()

        # Verify auth params are included
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["params"]["apitoken"] == "ABC123XYZ789TOKEN"
        assert call_kwargs["params"]["key"] == "value"

    @patch("requests.Session.request")
    def test_request_authentication_error(self, mock_request, client):
        """Test authentication error handling."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response

        with pytest.raises(PRTGAuthenticationError, match="Authentication failed"):
            client._request("test.json")

    @patch("requests.Session.request")
    def test_request_not_found_error(self, mock_request, client):
        """Test 404 error handling."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response

        with pytest.raises(PRTGNotFoundError, match="Resource not found"):
            client._request("test.json")

    @patch("requests.Session.request")
    def test_request_api_error(self, mock_request, client):
        """Test generic API error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_request.return_value = mock_response

        with pytest.raises(PRTGAPIError, match="API error: 500"):
            client._request("test.json")

    @patch("requests.Session.request")
    def test_request_connection_error(self, mock_request, client):
        """Test connection error handling."""
        mock_request.side_effect = requests.exceptions.ConnectionError("Connection refused")

        with pytest.raises(PRTGClientError, match="Connection error"):
            client._request("test.json")

    @patch("requests.Session.request")
    def test_request_ssl_error(self, mock_request, client):
        """Test SSL error handling."""
        mock_request.side_effect = requests.exceptions.SSLError("SSL verification failed")

        with pytest.raises(PRTGClientError, match="SSL verification failed"):
            client._request("test.json")

    @patch("requests.Session.request")
    def test_request_timeout(self, mock_request, client):
        """Test timeout error handling."""
        mock_request.side_effect = requests.exceptions.Timeout("Request timeout")

        with pytest.raises(PRTGClientError, match="Request timeout"):
            client._request("test.json")

    @patch("requests.Session.request")
    def test_get_devices(self, mock_request, client):
        """Test getting list of devices."""
        fixture_data = load_fixture("devices.json")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture_data
        mock_request.return_value = mock_response

        result = client.get_devices()

        assert result.total == 3
        assert len(result.devices) == 3
        assert result.devices[0].objid == "2001"
        assert result.devices[0].name == "web-server-01"
        assert result.devices[0].host == "192.168.1.10"

    @patch("requests.Session.request")
    def test_get_devices_with_filters(self, mock_request, client):
        """Test getting devices with filters."""
        fixture_data = load_fixture("devices.json")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture_data
        mock_request.return_value = mock_response

        result = client.get_devices(
            filter_status="down",
            filter_tags="production",
            filter_group="1000",
            count=10,
            start=0,
        )

        # Verify filters were applied in request
        call_kwargs = mock_request.call_args[1]
        params = call_kwargs["params"]
        assert params["filter_status"] == "5"  # 'down' mapped to status code
        assert params["filter_tags"] == "@tag(production)"
        assert params["filter_parentid"] == "1000"
        assert params["count"] == 10
        assert params["start"] == 0

    @patch("requests.Session.request")
    def test_get_devices_custom_columns(self, mock_request, client):
        """Test getting devices with custom columns."""
        fixture_data = load_fixture("devices.json")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture_data
        mock_request.return_value = mock_response

        result = client.get_devices(columns=["objid", "name", "host"])

        # Verify columns parameter
        call_kwargs = mock_request.call_args[1]
        params = call_kwargs["params"]
        assert params["columns"] == "objid,name,host"

    @patch("requests.Session.request")
    def test_get_device(self, mock_request, client):
        """Test getting a single device."""
        # Return single device in list
        single_device_response = {
            "prtg-version": "21.4.73.1234",
            "treesize": 1,
            "devices": [
                {
                    "objid": "2001",
                    "name": "web-server-01",
                    "device": "web-server-01",
                    "host": "192.168.1.10",
                    "probe": "Local Probe",
                    "group": "Web Servers",
                    "status": "Up",
                    "status_raw": "3",
                    "message": "OK",
                    "tags": "production",
                    "upsens": "10",
                    "downsens": "0",
                }
            ],
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = single_device_response
        mock_request.return_value = mock_response

        result = client.get_device("2001")

        assert result.objid == "2001"
        assert result.name == "web-server-01"
        assert result.host == "192.168.1.10"

        # Verify filter_objid was used
        call_kwargs = mock_request.call_args[1]
        params = call_kwargs["params"]
        assert params["filter_objid"] == "2001"

    @patch("requests.Session.request")
    def test_get_device_not_found(self, mock_request, client):
        """Test getting a device that doesn't exist."""
        empty_response = {
            "prtg-version": "21.4.73.1234",
            "treesize": 0,
            "devices": [],
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = empty_response
        mock_request.return_value = mock_response

        with pytest.raises(PRTGNotFoundError, match="Device not found: 9999"):
            client.get_device("9999")

    @patch("requests.Session.request")
    def test_get_devices_by_ids(self, mock_request, client):
        """Test getting multiple devices by IDs."""
        # Mock responses for each device
        def mock_response_generator(*args, **kwargs):
            device_id = kwargs["params"]["filter_objid"]
            if device_id == "2001":
                data = {
                    "devices": [
                        {
                            "objid": "2001",
                            "name": "web-server-01",
                            "device": "web-server-01",
                            "host": "192.168.1.10",
                            "status": "Up",
                            "tags": "",
                        }
                    ]
                }
            elif device_id == "2002":
                data = {
                    "devices": [
                        {
                            "objid": "2002",
                            "name": "db-server-01",
                            "device": "db-server-01",
                            "host": "192.168.1.20",
                            "status": "Up",
                            "tags": "",
                        }
                    ]
                }
            else:
                data = {"devices": []}

            response = Mock()
            response.status_code = 200
            response.json.return_value = data
            return response

        mock_request.side_effect = mock_response_generator

        result = client.get_devices_by_ids(["2001", "2002", "9999"])

        # Should return 2 devices (9999 doesn't exist)
        assert len(result) == 2
        assert result[0].objid == "2001"
        assert result[1].objid == "2002"

    @patch("requests.Session.request")
    def test_ping_success(self, mock_request, client):
        """Test successful ping."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"devices": []}
        mock_request.return_value = mock_response

        result = client.ping()
        assert result is True

    @patch("requests.Session.request")
    def test_ping_failure(self, mock_request, client):
        """Test ping failure."""
        mock_request.side_effect = requests.exceptions.ConnectionError("Connection refused")

        with pytest.raises(PRTGClientError):
            client.ping()

    def test_ssl_verification_disabled(self):
        """Test client with SSL verification disabled."""
        config = PRTGConfig(
            url="https://prtg.example.com",
            api_token="ABC123XYZ789TOKEN",
            verify_ssl=False,
        )
        client = PRTGClient(config)

        with patch("requests.Session.request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"test": "data"}
            mock_request.return_value = mock_response

            client._request("test.json")

            # Verify SSL verification is disabled
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["verify"] is False

    @patch("requests.Session.request")
    def test_move_device_success(self, mock_request, client):
        """Test successful device move."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Ok"
        mock_request.return_value = mock_response

        result = client.move_device("2001", "5666")

        assert result is True

        # Verify the correct endpoint and parameters were used
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "GET"
        assert "moveobjectnow.htm" in call_args[1]["url"]
        # Check parameters
        params = call_args[1]["params"]
        assert params["id"] == "2001"
        assert params["targetid"] == "5666"
        assert "apitoken" in params

    @patch("requests.Session.request")
    def test_move_device_failure(self, mock_request, client):
        """Test device move with API error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_request.return_value = mock_response

        with pytest.raises(PRTGAPIError):
            client.move_device("2001", "5666")

    @patch("requests.Session.request")
    def test_move_multiple_devices(self, mock_request, client):
        """Test moving multiple devices."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Ok"
        mock_request.return_value = mock_response

        device_ids = ["2001", "2002", "2003"]
        results = client.move_devices(device_ids, "5666")

        assert len(results) == 3
        assert all(result["success"] for result in results)
        assert mock_request.call_count == 3

    @patch("requests.Session.request")
    def test_move_multiple_devices_partial_failure(self, mock_request, client):
        """Test moving multiple devices with some failures."""
        def mock_response_generator(*args, **kwargs):
            device_id = kwargs["params"]["id"]
            response = Mock()
            if device_id == "2002":
                response.status_code = 500
                response.text = "Error"
            else:
                response.status_code = 200
                response.text = "Ok"
            return response

        mock_request.side_effect = mock_response_generator

        device_ids = ["2001", "2002", "2003"]
        results = client.move_devices(device_ids, "5666")

        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert results[2]["success"] is True
        assert "error" in results[1]
