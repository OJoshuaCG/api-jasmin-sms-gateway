import re

from pydantic import BaseModel, Field, field_validator

_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


class GroupCreate(BaseModel):
    gid: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description=(
            "Unique group identifier. Used to assign users to a permission group. "
            "Only letters, digits, underscores and hyphens allowed. "
            "Example: \"premium_customers\""
        ),
    )

    @field_validator("gid")
    @classmethod
    def validate_gid(cls, v: str) -> str:
        if not _ID_PATTERN.match(v):
            raise ValueError("gid only allows letters, digits, underscores and hyphens")
        return v


class GroupUpdate(BaseModel):
    enabled: bool = Field(
        ...,
        description=(
            "Enable (true) or disable (false) the group. "
            "Disabling a group blocks all users in it from sending MT messages."
        ),
    )


class GroupOut(BaseModel):
    gid: str
    enabled: bool
