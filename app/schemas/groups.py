from pydantic import BaseModel, Field


class GroupCreate(BaseModel):
    gid: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description=(
            "Unique group identifier. Used to assign users to a permission group. "
            "Example: \"premium_customers\""
        ),
    )


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
