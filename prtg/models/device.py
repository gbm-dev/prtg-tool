"""Pydantic models for PRTG Device objects."""

from typing import Optional, List
from pydantic import Field, field_validator

from prtg.models.base import (
    PRTGObjectModel,
    PRTGStatusMixin,
    PRTGPriorityMixin,
    PRTGListResponse,
)


class Device(PRTGObjectModel, PRTGStatusMixin, PRTGPriorityMixin):
    """Model for a PRTG Device object."""

    # Core device fields
    device: Optional[str] = Field(None, description="Device display name")
    host: Optional[str] = Field(None, description="IP address or hostname")
    probe: Optional[str] = Field(None, description="Probe name")
    group: Optional[str] = Field(None, description="Parent group name")
    parentid: Optional[str] = Field(None, description="Parent group ID")

    # Icon and visual
    icon: Optional[str] = Field(None, description="Device icon filename")

    # Location and metadata
    location: Optional[str] = Field(None, description="Physical location")
    comments: Optional[str] = Field(None, description="Device comments")

    # Sensor counts
    sensor_count: Optional[int] = Field(None, description="Total number of sensors")
    upsens: Optional[str] = Field(None, description="Number of sensors in Up status")
    downsens: Optional[str] = Field(None, description="Number of sensors in Down status")
    warnsens: Optional[str] = Field(None, description="Number of sensors in Warning status")
    pausedsens: Optional[str] = Field(None, description="Number of paused sensors")
    unusualsens: Optional[str] = Field(None, description="Number of sensors in Unusual status")
    undefinedsens: Optional[str] = Field(None, description="Number of sensors in Undefined status")
    partialdownsens: Optional[str] = Field(None, description="Number of sensors in Partial Down status")

    # Converted sensor counts (for convenience)
    sensor_count_up: Optional[int] = Field(None, description="Number of up sensors (int)")
    sensor_count_down: Optional[int] = Field(None, description="Number of down sensors (int)")
    sensor_count_warning: Optional[int] = Field(None, description="Number of warning sensors (int)")
    sensor_count_paused: Optional[int] = Field(None, description="Number of paused sensors (int)")
    sensor_count_unusual: Optional[int] = Field(None, description="Number of unusual sensors (int)")

    # Uptime/Downtime information
    lastup: Optional[str] = Field(None, description="Last time device was up")
    lastdown: Optional[str] = Field(None, description="Last time device was down")
    uptime: Optional[str] = Field(None, description="Uptime duration (human readable)")
    downtime: Optional[str] = Field(None, description="Downtime duration (human readable)")
    uptime_seconds: Optional[int] = Field(None, description="Uptime in seconds")
    downtime_seconds: Optional[int] = Field(None, description="Downtime in seconds")
    uptime_percent: Optional[str] = Field(None, description="Uptime percentage")

    # Additional metadata
    schedule: Optional[str] = Field(None, description="Monitoring schedule")
    access_rights: Optional[str] = Field(None, description="Access rights")
    dependencies: List[str] = Field(default_factory=list, description="Dependencies")

    @field_validator("parentid", mode="before")
    @classmethod
    def convert_parentid(cls, v):
        """Convert parentid to string if it's an integer."""
        if v is None:
            return None
        return str(v)

    @field_validator("upsens", "downsens", "warnsens", "pausedsens", "unusualsens", mode="before")
    @classmethod
    def convert_sensor_count(cls, v):
        """Convert sensor count to string if it's an integer."""
        if v is None:
            return None
        return str(v)

    def model_post_init(self, __context):
        """Post-initialization processing.

        Convert string sensor counts to integers for convenience fields.
        """
        if self.upsens is not None and self.sensor_count_up is None:
            try:
                self.sensor_count_up = int(self.upsens)
            except (ValueError, TypeError):
                pass

        if self.downsens is not None and self.sensor_count_down is None:
            try:
                self.sensor_count_down = int(self.downsens)
            except (ValueError, TypeError):
                pass

        if self.warnsens is not None and self.sensor_count_warning is None:
            try:
                self.sensor_count_warning = int(self.warnsens)
            except (ValueError, TypeError):
                pass

        if self.pausedsens is not None and self.sensor_count_paused is None:
            try:
                self.sensor_count_paused = int(self.pausedsens)
            except (ValueError, TypeError):
                pass

        if self.unusualsens is not None and self.sensor_count_unusual is None:
            try:
                self.sensor_count_unusual = int(self.unusualsens)
            except (ValueError, TypeError):
                pass


class DeviceListResponse(PRTGListResponse):
    """Model for PRTG device list API response."""

    devices: List[Device] = Field(default_factory=list, description="List of devices")

    @property
    def total(self) -> int:
        """Total number of devices in the response."""
        return len(self.devices)
