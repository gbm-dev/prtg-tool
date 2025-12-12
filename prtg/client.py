"""PRTG API Client."""

from typing import Optional, List, Dict, Any
import warnings
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

from prtg.config import PRTGConfig
from prtg.models.device import Device, DeviceListResponse
from prtg.models.group import Group, GroupListResponse
from prtg.models.sensor import Sensor, SensorListResponse


class PRTGClientError(Exception):
    """Base exception for PRTG client errors."""

    pass


class PRTGAuthenticationError(PRTGClientError):
    """Authentication error."""

    pass


class PRTGNotFoundError(PRTGClientError):
    """Resource not found error."""

    pass


class PRTGAPIError(PRTGClientError):
    """Generic API error."""

    pass


class PRTGClient:
    """Client for interacting with PRTG API."""

    def __init__(self, config: PRTGConfig):
        """Initialize PRTG API client.

        Args:
            config: PRTG configuration
        """
        self.config = config
        self.base_url = f"{config.url}/api"

        # Disable SSL warnings if verify_ssl is False
        if not config.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Create session with retry strategy
        self.session = requests.Session()

        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _build_auth_params(self) -> Dict[str, str]:
        """Build authentication parameters.

        Returns:
            Dictionary with apitoken
        """
        return {
            "apitoken": self.config.api_token,
        }

    def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
    ) -> Dict[str, Any]:
        """Make a request to the PRTG API.

        Args:
            endpoint: API endpoint (e.g., "table.json")
            params: Query parameters
            method: HTTP method

        Returns:
            JSON response as dictionary

        Raises:
            PRTGAuthenticationError: Authentication failed
            PRTGNotFoundError: Resource not found
            PRTGAPIError: Other API errors
        """
        url = f"{self.base_url}/{endpoint}"

        # Merge auth params with request params
        request_params = self._build_auth_params()
        if params:
            request_params.update(params)

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=request_params,
                verify=self.config.verify_ssl,
                timeout=30,
            )

            # Handle HTTP errors
            if response.status_code == 401:
                raise PRTGAuthenticationError("Authentication failed. Check username and passhash.")
            elif response.status_code == 404:
                raise PRTGNotFoundError(f"Resource not found: {endpoint}")
            elif response.status_code >= 400:
                raise PRTGAPIError(
                    f"API error: {response.status_code} - {response.text}"
                )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.SSLError as e:
            raise PRTGClientError(
                f"SSL verification failed. Use --no-verify-ssl to disable verification. Error: {e}"
            )
        except requests.exceptions.ConnectionError as e:
            raise PRTGClientError(f"Connection error: Unable to connect to {self.config.url}. Error: {e}")
        except requests.exceptions.Timeout as e:
            raise PRTGClientError(f"Request timeout: {e}")
        except requests.exceptions.RequestException as e:
            raise PRTGClientError(f"Request failed: {e}")

    def get_devices(
        self,
        columns: Optional[List[str]] = None,
        filter_status: Optional[str] = None,
        filter_tags: Optional[str] = None,
        filter_group: Optional[str] = None,
        count: Optional[int] = None,
        start: Optional[int] = None,
    ) -> DeviceListResponse:
        """Get list of devices from PRTG.

        Args:
            columns: List of columns to retrieve
            filter_status: Filter by status (up, down, warning, paused, unusual, unknown)
            filter_tags: Filter by tag
            filter_group: Filter by parent group ID
            count: Number of results to return (default: 500, use None for all)
            start: Starting offset for pagination

        Returns:
            DeviceListResponse with list of devices

        Raises:
            PRTGClientError: If API request fails
        """
        # Default columns to retrieve
        if columns is None:
            columns = [
                "objid",
                "name",
                "device",
                "host",
                "probe",
                "group",
                "parentid",
                "status",
                "status_raw",
                "message",
                "tags",
                "priority",
                "upsens",
                "downsens",
                "warnsens",
                "pausedsens",
                "unusualsens",
            ]

        params = {
            "content": "devices",
            "columns": ",".join(columns),
        }

        # Add optional filters
        if filter_status:
            # Map friendly status names to raw codes
            status_map = {
                "up": "3",
                "down": "5",
                "warning": "4",
                "paused": "7",
                "unusual": "10",
                "unknown": "1",
            }
            params["filter_status"] = status_map.get(filter_status.lower(), filter_status)

        if filter_tags:
            params["filter_tags"] = f"@tag({filter_tags})"

        if filter_group:
            params["filter_parentid"] = filter_group

        if count is not None:
            params["count"] = count
        else:
            params["count"] = "*"  # Get all devices

        if start is not None:
            params["start"] = start

        response_data = self._request("table.json", params=params)
        return DeviceListResponse(**response_data)

    def get_device(self, device_id: str, columns: Optional[List[str]] = None) -> Device:
        """Get a single device by ID.

        Args:
            device_id: Device object ID
            columns: List of columns to retrieve

        Returns:
            Device object

        Raises:
            PRTGNotFoundError: If device not found
            PRTGClientError: If API request fails
        """
        # Use default columns if not specified
        if columns is None:
            columns = [
                "objid",
                "name",
                "device",
                "host",
                "probe",
                "group",
                "parentid",
                "status",
                "status_raw",
                "message",
                "tags",
                "priority",
                "upsens",
                "downsens",
                "warnsens",
                "pausedsens",
                "unusualsens",
            ]

        # Get the specific device using table.json with filter
        params = {
            "content": "devices",
            "columns": ",".join(columns),
            "filter_objid": device_id,
        }

        response_data = self._request("table.json", params=params)
        device_list = DeviceListResponse(**response_data)

        if not device_list.devices:
            raise PRTGNotFoundError(f"Device not found: {device_id}")

        return device_list.devices[0]

    def get_devices_by_ids(
        self, device_ids: List[str], columns: Optional[List[str]] = None
    ) -> List[Device]:
        """Get multiple devices by IDs.

        Args:
            device_ids: List of device object IDs
            columns: List of columns to retrieve

        Returns:
            List of Device objects

        Raises:
            PRTGClientError: If API request fails
        """
        devices = []
        for device_id in device_ids:
            try:
                device = self.get_device(device_id, columns=columns)
                devices.append(device)
            except PRTGNotFoundError:
                # Skip devices that don't exist
                continue

        return devices

    def get_sensors(
        self,
        columns: Optional[List[str]] = None,
        filter_status: Optional[str] = None,
        filter_tags: Optional[str] = None,
        filter_device: Optional[str] = None,
        count: Optional[int] = None,
        start: Optional[int] = None,
    ) -> SensorListResponse:
        """Get list of sensors from PRTG.

        Args:
            columns: List of columns to retrieve
            filter_status: Filter by status (up, down, warning, paused, unusual, unknown)
            filter_tags: Filter by tag
            filter_device: Filter by parent device ID
            count: Number of results to return (default: 500, use None for all)
            start: Starting offset for pagination

        Returns:
            SensorListResponse with list of sensors

        Raises:
            PRTGClientError: If API request fails
        """
        # Default columns to retrieve
        if columns is None:
            columns = [
                "objid",
                "name",
                "sensor",
                "device",
                "group",
                "probe",
                "parentid",
                "status",
                "status_raw",
                "message",
                "sensor_type",
                "interval",
                "lastvalue",
                "lastmessage",
                "downtime",
                "uptime",
                "priority",
                "tags",
            ]

        params = {
            "content": "sensors",
            "columns": ",".join(columns),
        }

        # Add optional filters
        if filter_status:
            # Map friendly status names to raw codes
            status_map = {
                "up": "3",
                "down": "5",
                "warning": "4",
                "paused": "7",
                "unusual": "10",
                "unknown": "1",
            }
            params["filter_status"] = status_map.get(filter_status.lower(), filter_status)

        if filter_tags:
            params["filter_tags"] = f"@tag({filter_tags})"

        if filter_device:
            params["filter_parentid"] = filter_device

        if count is not None:
            params["count"] = count
        else:
            params["count"] = "*"  # Get all sensors

        if start is not None:
            params["start"] = start

        response_data = self._request("table.json", params=params)
        return SensorListResponse(**response_data)

    def get_sensor(self, sensor_id: str, columns: Optional[List[str]] = None) -> Sensor:
        """Get a single sensor by ID.

        Args:
            sensor_id: Sensor object ID
            columns: List of columns to retrieve

        Returns:
            Sensor object

        Raises:
            PRTGNotFoundError: If sensor not found
            PRTGClientError: If API request fails
        """
        # Use default columns if not specified
        if columns is None:
            columns = [
                "objid",
                "name",
                "sensor",
                "device",
                "group",
                "probe",
                "parentid",
                "status",
                "status_raw",
                "message",
                "sensor_type",
                "interval",
                "lastvalue",
                "lastmessage",
                "downtime",
                "uptime",
                "priority",
                "tags",
            ]

        # Get the specific sensor using table.json with filter
        params = {
            "content": "sensors",
            "columns": ",".join(columns),
            "filter_objid": sensor_id,
        }

        response_data = self._request("table.json", params=params)
        sensor_list = SensorListResponse(**response_data)

        if not sensor_list.sensors:
            raise PRTGNotFoundError(f"Sensor not found: {sensor_id}")

        return sensor_list.sensors[0]

    def get_sensors_by_ids(
        self, sensor_ids: List[str], columns: Optional[List[str]] = None
    ) -> List[Sensor]:
        """Get multiple sensors by IDs.

        Args:
            sensor_ids: List of sensor object IDs
            columns: List of columns to retrieve

        Returns:
            List of Sensor objects

        Raises:
            PRTGClientError: If API request fails
        """
        sensors = []
        for sensor_id in sensor_ids:
            try:
                sensor = self.get_sensor(sensor_id, columns=columns)
                sensors.append(sensor)
            except PRTGNotFoundError:
                # Skip sensors that don't exist
                continue

        return sensors

    def get_sensor_historicdata(
        self,
        sensor_id: str,
        start_date: str,
        end_date: str,
        avg_interval: int = 0,
        output_format: str = "csv",
    ):
        """Get historic data for a sensor.

        Args:
            sensor_id: Sensor object ID
            start_date: Start date/time in format yyyy-MM-dd-HH-mm-ss
            end_date: End date/time in format yyyy-MM-dd-HH-mm-ss
            avg_interval: Averaging interval in seconds
                         0=raw, 60=1min, 3600=1hour, 86400=1day
            output_format: Output format - "csv" or "json"

        Returns:
            For CSV: Raw CSV string
            For JSON: Dictionary with historic data

        Raises:
            PRTGAPIError: If API request fails or rate limit exceeded
            PRTGClientError: If request fails
        """
        # Build endpoint URL based on format
        endpoint = f"historicdata.{output_format}"

        params = {
            "id": sensor_id,
            "sdate": start_date,
            "edate": end_date,
            "avg": avg_interval,
        }

        try:
            url = f"{self.base_url}/{endpoint}"

            # Merge auth params
            request_params = self._build_auth_params()
            request_params.update(params)

            response = self.session.request(
                method="GET",
                url=url,
                params=request_params,
                verify=self.config.verify_ssl,
                timeout=30,
            )

            # Handle rate limit specifically
            if response.status_code == 429:
                raise PRTGAPIError(
                    "Rate limit exceeded (5 requests per minute for historic data). "
                    "Please wait 60 seconds before trying again."
                )

            # Handle other HTTP errors
            if response.status_code == 401:
                raise PRTGAuthenticationError("Authentication failed. Check API token.")
            elif response.status_code == 404:
                raise PRTGNotFoundError(f"Sensor not found: {sensor_id}")
            elif response.status_code >= 400:
                raise PRTGAPIError(
                    f"API error: {response.status_code} - {response.text}"
                )

            response.raise_for_status()

            # Return based on format
            if output_format == "csv":
                return response.text
            else:  # json
                return response.json()

        except requests.exceptions.SSLError as e:
            raise PRTGClientError(
                f"SSL verification failed. Use --no-verify-ssl to disable verification. Error: {e}"
            )
        except requests.exceptions.ConnectionError as e:
            raise PRTGClientError(f"Connection error: Unable to connect to {self.config.url}. Error: {e}")
        except requests.exceptions.Timeout as e:
            raise PRTGClientError(f"Request timeout: {e}")
        except requests.exceptions.RequestException as e:
            raise PRTGClientError(f"Request failed: {e}")

    def get_groups(
        self,
        columns: Optional[List[str]] = None,
        filter_parentid: Optional[str] = None,
        count: Optional[int] = None,
        start: Optional[int] = None,
    ) -> GroupListResponse:
        """Get list of groups from PRTG.

        Args:
            columns: List of columns to retrieve
            filter_parentid: Filter by parent group ID
            count: Number of results to return (default: 500, use None for all)
            start: Starting offset for pagination

        Returns:
            GroupListResponse with list of groups

        Raises:
            PRTGClientError: If API request fails
        """
        # Default columns to retrieve
        if columns is None:
            columns = [
                "objid",
                "name",
                "probe",
                "group",
                "parentid",
            ]

        params = {
            "content": "groups",
            "columns": ",".join(columns),
        }

        # Add optional filters
        if filter_parentid:
            params["filter_parentid"] = filter_parentid

        if count is not None:
            params["count"] = count
        else:
            params["count"] = "*"  # Get all groups

        if start is not None:
            params["start"] = start

        response_data = self._request("table.json", params=params)
        return GroupListResponse(**response_data)

    def get_group(self, group_id: str, columns: Optional[List[str]] = None) -> Group:
        """Get a single group by ID.

        Args:
            group_id: Group object ID
            columns: List of columns to retrieve

        Returns:
            Group object

        Raises:
            PRTGNotFoundError: If group not found
            PRTGClientError: If API request fails
        """
        # Use default columns if not specified
        if columns is None:
            columns = [
                "objid",
                "name",
                "probe",
                "group",
                "parentid",
            ]

        # Get the specific group using table.json with filter
        params = {
            "content": "groups",
            "columns": ",".join(columns),
            "filter_objid": group_id,
        }

        response_data = self._request("table.json", params=params)
        group_list = GroupListResponse(**response_data)

        if not group_list.groups:
            raise PRTGNotFoundError(f"Group not found: {group_id}")

        return group_list.groups[0]

    def get_groups_by_ids(
        self, group_ids: List[str], columns: Optional[List[str]] = None
    ) -> List[Group]:
        """Get multiple groups by IDs.

        Args:
            group_ids: List of group object IDs
            columns: List of columns to retrieve

        Returns:
            List of Group objects

        Raises:
            PRTGClientError: If API request fails
        """
        groups = []
        for group_id in group_ids:
            try:
                group = self.get_group(group_id, columns=columns)
                groups.append(group)
            except PRTGNotFoundError:
                # Skip groups that don't exist
                continue

        return groups

    def move_device(self, device_id: str, target_group_id: str) -> bool:
        """Move a device to a different group.

        Args:
            device_id: Device object ID to move
            target_group_id: Target group ID to move the device to

        Returns:
            True if move was successful

        Raises:
            PRTGAPIError: If API request fails
            PRTGClientError: If connection fails
        """
        # moveobjectnow.htm uses HTTP GET with all parameters in URL
        params = {
            "id": device_id,
            "targetid": target_group_id,
        }

        try:
            # moveobjectnow.htm is not under /api/, use config.url directly
            response = self.session.request(
                method="GET",
                url=f"{self.config.url}/moveobjectnow.htm",
                params={**self._build_auth_params(), **params},
                verify=self.config.verify_ssl,
                timeout=30,
            )

            # Handle HTTP errors
            if response.status_code == 401:
                raise PRTGAuthenticationError("Authentication failed. Check API token.")
            elif response.status_code == 404:
                raise PRTGNotFoundError(f"Device or target group not found: {device_id} -> {target_group_id}")
            elif response.status_code >= 400:
                raise PRTGAPIError(
                    f"API error: {response.status_code} - {response.text}"
                )

            response.raise_for_status()

            # PRTG returns plain text for moveobjectnow.htm
            # Successful response typically contains "Ok" (case insensitive)
            response_text = response.text.strip().lower()
            if "ok" in response_text:
                return True
            else:
                raise PRTGAPIError(f"Unexpected response from move operation: {response.text}")

        except requests.exceptions.SSLError as e:
            raise PRTGClientError(
                f"SSL verification failed. Use --no-verify-ssl to disable verification. Error: {e}"
            )
        except requests.exceptions.ConnectionError as e:
            raise PRTGClientError(f"Connection error: Unable to connect to {self.config.url}. Error: {e}")
        except requests.exceptions.Timeout as e:
            raise PRTGClientError(f"Request timeout: {e}")
        except requests.exceptions.RequestException as e:
            raise PRTGClientError(f"Request failed: {e}")

    def move_devices(
        self, device_ids: List[str], target_group_id: str
    ) -> List[Dict[str, Any]]:
        """Move multiple devices to a different group.

        Args:
            device_ids: List of device object IDs to move
            target_group_id: Target group ID to move the devices to

        Returns:
            List of dictionaries with results for each device:
            [{"device_id": "2001", "success": True}, ...]

        Note:
            This method continues moving devices even if some fail.
            Check the "success" field in each result.
        """
        results = []
        for device_id in device_ids:
            try:
                self.move_device(device_id, target_group_id)
                results.append({
                    "device_id": device_id,
                    "success": True,
                })
            except (PRTGClientError, PRTGAPIError, PRTGNotFoundError) as e:
                results.append({
                    "device_id": device_id,
                    "success": False,
                    "error": str(e),
                })

        return results

    def ping(self) -> bool:
        """Test connection to PRTG server.

        Returns:
            True if connection successful

        Raises:
            PRTGClientError: If connection fails
        """
        try:
            self._request("table.json", params={"content": "devices", "count": "1"})
            return True
        except PRTGClientError:
            raise
