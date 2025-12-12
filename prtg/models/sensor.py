"""Pydantic models for PRTG Sensor objects."""

from typing import Optional, List
from pydantic import Field, field_validator

from prtg.models.base import (
    PRTGObjectModel,
    PRTGStatusMixin,
    PRTGPriorityMixin,
    PRTGListResponse,
)


class Sensor(PRTGObjectModel, PRTGStatusMixin, PRTGPriorityMixin):
    """Model for a PRTG Sensor object."""

    # Core sensor fields
    sensor: Optional[str] = Field(None, description="Sensor display name")
    device: Optional[str] = Field(None, description="Parent device name")
    group: Optional[str] = Field(None, description="Parent group name")
    probe: Optional[str] = Field(None, description="Probe name")
    parentid: Optional[str] = Field(None, description="Parent device ID")

    # Sensor-specific fields
    sensor_type: Optional[str] = Field(None, description="Sensor type (Ping, HTTP, SNMP, etc.)")
    interval: Optional[str] = Field(None, description="Scanning interval")
    lastvalue: Optional[str] = Field(None, description="Last sensor value")
    lastmessage: Optional[str] = Field(None, description="Last message from sensor")

    # Uptime/Downtime information
    downtime: Optional[str] = Field(None, description="Downtime duration (human readable)")
    uptime: Optional[str] = Field(None, description="Uptime duration (human readable)")
    downtime_seconds: Optional[int] = Field(None, description="Downtime in seconds")
    uptime_seconds: Optional[int] = Field(None, description="Uptime in seconds")
    downtime_percent: Optional[str] = Field(None, description="Downtime percentage")
    uptime_percent: Optional[str] = Field(None, description="Uptime percentage")

    # Additional metadata
    lastup: Optional[str] = Field(None, description="Last time sensor was up")
    lastdown: Optional[str] = Field(None, description="Last time sensor was down")
    lastcheck: Optional[str] = Field(None, description="Last time sensor was checked")
    icon: Optional[str] = Field(None, description="Sensor icon filename")
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


class SensorListResponse(PRTGListResponse):
    """Model for PRTG sensor list API response."""

    sensors: List[Sensor] = Field(default_factory=list, description="List of sensors")

    @property
    def total(self) -> int:
        """Total number of sensors in the response."""
        return len(self.sensors)
