"""Tests for PRTG group functionality."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from prtg.client import (
    PRTGClient,
    PRTGClientError,
    PRTGNotFoundError,
)
from prtg.config import PRTGConfig
from prtg.models.group import Group, GroupListResponse


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


class TestGroupModel:
    """Tests for Group Pydantic model."""

    def test_basic_group_creation(self):
        """Test creating a basic group."""
        group = Group(
            objid="2074",
            name="AmTrack",
            parentid="2060",
        )
        assert group.objid == "2074"
        assert group.name == "AmTrack"
        assert group.parentid == "2060"

    def test_group_with_all_fields(self):
        """Test group with all fields."""
        group = Group(
            objid="2074",
            name="AmTrack",
            probe="AZU-SUS-PRTGP01",
            group="AmTrack",
            parentid="2060",
            objid_raw=2074,
            name_raw="AmTrack",
            probe_raw="AZU-SUS-PRTGP01",
            group_raw="AmTrack",
            parentid_raw=2060,
        )
        assert group.objid == "2074"
        assert group.objid_raw == 2074
        assert group.probe == "AZU-SUS-PRTGP01"

    def test_group_objid_conversion(self):
        """Test that objid is converted to string."""
        group = Group(
            objid=2074,
            name="AmTrack",
            parentid=2060,
        )
        assert group.objid == "2074"
        assert group.parentid == "2060"


class TestGroupListResponse:
    """Tests for GroupListResponse model."""

    def test_empty_group_list(self):
        """Test empty group list response."""
        response = GroupListResponse(groups=[], treesize=0)
        assert len(response.groups) == 0
        assert response.total == 0
        assert response.treesize == 0

    def test_group_list_from_fixture(self):
        """Test parsing group list from fixture data."""
        fixture_data = load_fixture("groups.json")
        response = GroupListResponse(**fixture_data)

        assert response.total == 5
        assert response.treesize == 5
        assert len(response.groups) == 5
        assert response.groups[0].objid == "0"
        assert response.groups[0].name == "Root"
        assert response.groups[1].objid == "2074"
        assert response.groups[1].name == "AmTrack"


class TestPRTGClientGroups:
    """Tests for PRTG client group methods."""

    @patch("requests.Session.request")
    def test_get_groups(self, mock_request, client):
        """Test getting list of groups."""
        fixture_data = load_fixture("groups.json")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture_data
        mock_request.return_value = mock_response

        result = client.get_groups()

        assert result.total == 5
        assert len(result.groups) == 5
        assert result.groups[0].objid == "0"
        assert result.groups[0].name == "Root"

    @patch("requests.Session.request")
    def test_get_groups_with_parent_filter(self, mock_request, client):
        """Test getting groups with parent filter."""
        fixture_data = load_fixture("groups.json")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture_data
        mock_request.return_value = mock_response

        result = client.get_groups(filter_parentid="2074")

        # Verify filter was applied in request
        call_kwargs = mock_request.call_args[1]
        params = call_kwargs["params"]
        assert params["filter_parentid"] == "2074"

    @patch("requests.Session.request")
    def test_get_group(self, mock_request, client):
        """Test getting a single group."""
        single_group_response = {
            "prtg-version": "24.3.100.1361",
            "treesize": 1,
            "groups": [
                {
                    "objid": "2074",
                    "objid_raw": 2074,
                    "probe": "AZU-SUS-PRTGP01",
                    "group": "AmTrack",
                    "name": "AmTrack",
                    "parentid": "2060",
                    "parentid_raw": 2060,
                }
            ],
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = single_group_response
        mock_request.return_value = mock_response

        result = client.get_group("2074")

        assert result.objid == "2074"
        assert result.name == "AmTrack"
        assert result.parentid == "2060"

        # Verify filter_objid was used
        call_kwargs = mock_request.call_args[1]
        params = call_kwargs["params"]
        assert params["filter_objid"] == "2074"

    @patch("requests.Session.request")
    def test_get_group_not_found(self, mock_request, client):
        """Test getting a group that doesn't exist."""
        empty_response = {
            "prtg-version": "24.3.100.1361",
            "treesize": 0,
            "groups": [],
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = empty_response
        mock_request.return_value = mock_response

        with pytest.raises(PRTGNotFoundError, match="Group not found: 9999"):
            client.get_group("9999")

    @patch("requests.Session.request")
    def test_get_groups_by_ids(self, mock_request, client):
        """Test getting multiple groups by IDs."""
        def mock_response_generator(*args, **kwargs):
            group_id = kwargs["params"]["filter_objid"]
            if group_id == "2074":
                data = {
                    "groups": [
                        {
                            "objid": "2074",
                            "name": "AmTrack",
                            "probe": "AZU-SUS-PRTGP01",
                            "group": "AmTrack",
                            "parentid": "2060",
                        }
                    ]
                }
            elif group_id == "2136":
                data = {
                    "groups": [
                        {
                            "objid": "2136",
                            "name": "IBM Cloud",
                            "probe": "AZU-SUS-PRTGP01",
                            "group": "IBM Cloud",
                            "parentid": "2074",
                        }
                    ]
                }
            else:
                data = {"groups": []}

            response = Mock()
            response.status_code = 200
            response.json.return_value = data
            return response

        mock_request.side_effect = mock_response_generator

        result = client.get_groups_by_ids(["2074", "2136", "9999"])

        # Should return 2 groups (9999 doesn't exist)
        assert len(result) == 2
        assert result[0].objid == "2074"
        assert result[1].objid == "2136"
