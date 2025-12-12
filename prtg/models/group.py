"""Pydantic models for PRTG groups."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class Group(BaseModel):
    """PRTG group object.

    Represents a group in the PRTG hierarchy which can contain
    devices and other groups.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="ignore",
    )

    objid: str = Field(..., description="Object ID")
    name: str = Field(..., description="Group name")
    probe: str = Field(default="", description="Probe name")
    group: str = Field(default="", description="Group path/hierarchy")
    parentid: str = Field(..., description="Parent group ID")

    # Optional fields
    objid_raw: Optional[int] = Field(None, description="Raw object ID")
    name_raw: Optional[str] = Field(None, description="Raw group name")
    probe_raw: Optional[str] = Field(None, description="Raw probe name")
    group_raw: Optional[str] = Field(None, description="Raw group path")
    parentid_raw: Optional[int] = Field(None, description="Raw parent ID")

    @field_validator("objid", "parentid", mode="before")
    @classmethod
    def convert_to_string(cls, v):
        """Convert objid and parentid to strings."""
        if v is None:
            return ""
        return str(v)

    @field_validator("name", "probe", "group", mode="before")
    @classmethod
    def strip_whitespace(cls, v):
        """Strip whitespace from string fields."""
        if isinstance(v, str):
            return v.strip()
        return v


class GroupListResponse(BaseModel):
    """Response from PRTG API for group list.

    Contains metadata about the response and a list of groups.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    groups: List[Group] = Field(default_factory=list, description="List of groups")
    treesize: int = Field(0, description="Total number of groups in tree")
    prtg_version: Optional[str] = Field(None, alias="prtg-version", description="PRTG version")

    @property
    def total(self) -> int:
        """Total number of groups returned."""
        return len(self.groups)
