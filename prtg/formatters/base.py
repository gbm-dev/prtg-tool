"""Base formatter classes for output formatting."""

from abc import ABC, abstractmethod
from typing import Any, List
from prtg.models.device import Device, DeviceListResponse
from prtg.models.sensor import Sensor, SensorListResponse


class Formatter(ABC):
    """Abstract base class for output formatters."""

    @abstractmethod
    def format_devices(self, devices: DeviceListResponse) -> str:
        """Format a list of devices.

        Args:
            devices: DeviceListResponse object

        Returns:
            Formatted string
        """
        pass

    @abstractmethod
    def format_device(self, device: Device) -> str:
        """Format a single device.

        Args:
            device: Device object

        Returns:
            Formatted string
        """
        pass

    @abstractmethod
    def format_sensors(self, sensors: SensorListResponse) -> str:
        """Format a list of sensors.

        Args:
            sensors: SensorListResponse object

        Returns:
            Formatted string
        """
        pass

    @abstractmethod
    def format_sensor(self, sensor: Sensor) -> str:
        """Format a single sensor.

        Args:
            sensor: Sensor object

        Returns:
            Formatted string
        """
        pass

    @abstractmethod
    def format_error(self, error: Exception) -> str:
        """Format an error message.

        Args:
            error: Exception object

        Returns:
            Formatted error string
        """
        pass


class FormatterFactory:
    """Factory for creating formatter instances."""

    _formatters = {}

    @classmethod
    def register(cls, name: str, formatter_class: type):
        """Register a formatter class.

        Args:
            name: Formatter name (e.g., 'json', 'csv')
            formatter_class: Formatter class to register
        """
        cls._formatters[name] = formatter_class

    @classmethod
    def create(cls, name: str, **kwargs) -> Formatter:
        """Create a formatter instance.

        Args:
            name: Formatter name
            **kwargs: Additional arguments for formatter

        Returns:
            Formatter instance

        Raises:
            ValueError: If formatter not found
        """
        if name not in cls._formatters:
            raise ValueError(
                f"Unknown formatter: {name}. Available: {', '.join(cls._formatters.keys())}"
            )
        return cls._formatters[name](**kwargs)

    @classmethod
    def list_formatters(cls) -> List[str]:
        """List available formatters.

        Returns:
            List of formatter names
        """
        return list(cls._formatters.keys())
