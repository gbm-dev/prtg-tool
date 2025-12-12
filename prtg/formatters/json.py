"""JSON formatter for PRTG CLI output."""

import json
from typing import List
from prtg.formatters.base import Formatter, FormatterFactory
from prtg.models.device import Device, DeviceListResponse
from prtg.models.group import Group, GroupListResponse
from prtg.models.sensor import Sensor, SensorListResponse


class JSONFormatter(Formatter):
    """Formatter for JSON output."""

    def __init__(self, pretty: bool = False):
        """Initialize JSON formatter.

        Args:
            pretty: Enable pretty-printing with indentation
        """
        self.pretty = pretty

    def _to_json(self, data: any) -> str:
        """Convert data to JSON string.

        Args:
            data: Data to convert

        Returns:
            JSON string
        """
        if self.pretty:
            return json.dumps(data, indent=2, ensure_ascii=False)
        return json.dumps(data, ensure_ascii=False)

    def format_devices(self, devices: DeviceListResponse) -> str:
        """Format a list of devices as JSON.

        Args:
            devices: DeviceListResponse object

        Returns:
            JSON string
        """
        # Convert devices to list of dicts
        devices_data = [device.model_dump(exclude_none=True) for device in devices.devices]
        return self._to_json(devices_data)

    def format_device(self, device: Device) -> str:
        """Format a single device as JSON.

        Args:
            device: Device object

        Returns:
            JSON string
        """
        device_data = device.model_dump(exclude_none=True)
        return self._to_json(device_data)

    def format_groups(self, groups: GroupListResponse) -> str:
        """Format a list of groups as JSON.

        Args:
            groups: GroupListResponse object

        Returns:
            JSON string
        """
        # Convert groups to list of dicts
        groups_data = [group.model_dump(exclude_none=True) for group in groups.groups]
        return self._to_json(groups_data)

    def format_group(self, group: Group) -> str:
        """Format a single group as JSON.

        Args:
            group: Group object

        Returns:
            JSON string
        """
        group_data = group.model_dump(exclude_none=True)
        return self._to_json(group_data)

    def format_sensors(self, sensors: SensorListResponse) -> str:
        """Format a list of sensors as JSON.

        Args:
            sensors: SensorListResponse object

        Returns:
            JSON string
        """
        # Convert sensors to list of dicts
        sensors_data = [sensor.model_dump(exclude_none=True) for sensor in sensors.sensors]
        return self._to_json(sensors_data)

    def format_sensor(self, sensor: Sensor) -> str:
        """Format a single sensor as JSON.

        Args:
            sensor: Sensor object

        Returns:
            JSON string
        """
        sensor_data = sensor.model_dump(exclude_none=True)
        return self._to_json(sensor_data)

    def format_move_results(self, results: List[dict]) -> str:
        """Format device move results as JSON.

        Args:
            results: List of move operation results

        Returns:
            JSON string
        """
        return self._to_json(results)

    def format_error(self, error: Exception) -> str:
        """Format an error message as JSON.

        Args:
            error: Exception object

        Returns:
            JSON error string
        """
        error_data = {
            "error": {
                "type": error.__class__.__name__,
                "message": str(error),
            }
        }
        return self._to_json(error_data)


# Register JSON formatter
FormatterFactory.register("json", JSONFormatter)
