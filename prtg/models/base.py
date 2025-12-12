"""Base Pydantic models for PRTG API responses."""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class PRTGBaseModel(BaseModel):
    """Base model for all PRTG objects."""

    model_config = {
        "extra": "ignore",  # Ignore extra fields from API
        "str_strip_whitespace": True,  # Strip whitespace from strings
        "populate_by_name": True,  # Allow both field name and alias
    }


class PRTGObjectModel(PRTGBaseModel):
    """Base model for PRTG objects with common fields."""

    objid: str = Field(..., description="Unique object ID")
    name: str = Field(..., description="Object name")
    tags: List[str] = Field(default_factory=list, description="Object tags")

    @field_validator("objid", mode="before")
    @classmethod
    def convert_objid(cls, v):
        """Convert objid to string if it's an integer."""
        if v is None:
            return ""
        return str(v)

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        """Parse tags from PRTG API response.

        PRTG returns tags as a space-separated string.
        We convert it to a list of strings.
        """
        if isinstance(v, str):
            # PRTG returns tags as space-separated string
            return [tag.strip() for tag in v.split() if tag.strip()]
        elif isinstance(v, list):
            return v
        return []


class PRTGStatusMixin(PRTGBaseModel):
    """Mixin for objects with status fields."""

    status: str = Field(..., description="Status text (Up, Down, Warning, etc.)")
    status_raw: Optional[str] = Field(None, description="Raw numeric status code")
    message: str = Field(default="", description="Status message")

    @field_validator("status_raw", mode="before")
    @classmethod
    def convert_status_raw(cls, v):
        """Convert status_raw to string if it's an integer."""
        if v is None:
            return None
        return str(v)


class PRTGPriorityMixin(PRTGBaseModel):
    """Mixin for objects with priority fields."""

    priority: Optional[str] = Field(None, description="Priority level")
    priority_raw: Optional[str] = Field(None, description="Raw priority value")

    @field_validator("priority_raw", mode="before")
    @classmethod
    def convert_priority_raw(cls, v):
        """Convert priority_raw to string if it's an integer."""
        if v is None:
            return None
        return str(v)


class PRTGListResponse(PRTGBaseModel):
    """Base model for PRTG API list responses."""

    prtg_version: Optional[str] = Field(None, alias="prtg-version", description="PRTG version")
    treesize: Optional[int] = Field(None, description="Total number of objects in tree")
