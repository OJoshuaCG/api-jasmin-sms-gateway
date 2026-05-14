from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.utils.validators import validate_no_control_chars, validate_identifier

# Interceptors run Python scripts on every message before routing.
# The script file is saved to JASMIN_SCRIPTS_DIR and referenced with python3(path) syntax.
# Scripts must be valid Python modules (no bare `return` at module level).
# The `routable` object is injected into the script's namespace by Jasmin.
# Example minimal script: "# pass-through\n" (empty module — Jasmin routes normally)
# Example blocking script: "routable.reject()\n"

MtInterceptorType = Literal["DefaultInterceptor", "StaticMTInterceptor"]
MoInterceptorType = Literal["DefaultInterceptor", "StaticMOInterceptor"]


class MtInterceptorCreate(BaseModel):
    type: MtInterceptorType = Field(
        ...,
        description=(
            "DefaultInterceptor: applies to all MT messages (no filter needed). "
            "StaticMTInterceptor: applies only to messages matching the given filters."
        ),
    )
    order: int = Field(
        ...,
        ge=0,
        description=(
            "Evaluation priority. Lower order = evaluated first. "
            "DefaultInterceptor is typically at order 0."
        ),
    )
    filters: list[str] = Field(
        default=[],
        description=(
            "List of filter FIDs. Required for StaticMTInterceptor; ignored for DefaultInterceptor. "
            "Filters must exist in Jasmin before referencing them here. "
            "Example: [\"my_filter\"]"
        ),
    )
    script: str = Field(
        ...,
        description=(
            "Valid Python module source code. Saved to disk and loaded by Jasmin. "
            "The `routable` object is available in the script namespace. "
            "Must NOT contain bare `return` statements at module level. "
            "Example: \"# pass-through interceptor\\n\" or \"routable.reject()\\n\""
        ),
    )

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v: list[str]) -> list[str]:
        for item in v:
            validate_identifier(item, "filters item")
        return v

    @field_validator("script")
    @classmethod
    def valid_python(cls, v: str) -> str:
        try:
            compile(v, "<interceptor_script>", "exec")
        except SyntaxError as e:
            raise ValueError(f"Script is not valid Python: {e}") from e
        return v


class MtInterceptorUpdate(BaseModel):
    filters: list[str] | None = Field(
        default=None,
        description="Replace the filter list. Pass empty list [] to remove all filters.",
    )
    script: str | None = Field(
        default=None,
        description=(
            "New Python script source. If omitted, the existing script on disk is reused. "
            "If the script file was deleted, this field becomes required."
        ),
    )

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            for item in v:
                validate_identifier(item, "filters item")
        return v

    @field_validator("script")
    @classmethod
    def valid_python(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            compile(v, "<interceptor_script>", "exec")
        except SyntaxError as e:
            raise ValueError(f"Script is not valid Python: {e}") from e
        return v


class InterceptorOut(BaseModel):
    order: int
    type: str
    filters: list[str]
    script_path: str  # absolute path on disk where the script is stored


class MoInterceptorCreate(BaseModel):
    type: MoInterceptorType = Field(
        ...,
        description=(
            "DefaultInterceptor: applies to all MO messages. "
            "StaticMOInterceptor: applies only to messages matching the given filters."
        ),
    )
    order: int = Field(..., ge=0, description="Evaluation priority. Lower order = evaluated first.")
    filters: list[str] = Field(
        default=[],
        description=(
            "List of filter FIDs. Required for StaticMOInterceptor; ignored for DefaultInterceptor."
        ),
    )
    script: str = Field(
        ...,
        description=(
            "Valid Python module source code loaded by Jasmin. "
            "`routable` is available in the script namespace. "
            "Example: \"# pass-through\\n\""
        ),
    )

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v: list[str]) -> list[str]:
        for item in v:
            validate_identifier(item, "filters item")
        return v

    @field_validator("script")
    @classmethod
    def valid_python(cls, v: str) -> str:
        try:
            compile(v, "<interceptor_script>", "exec")
        except SyntaxError as e:
            raise ValueError(f"Script is not valid Python: {e}") from e
        return v


class MoInterceptorUpdate(BaseModel):
    filters: list[str] | None = Field(default=None, description="Replace the filter list.")
    script: str | None = Field(
        default=None,
        description="New Python script source. If omitted, reuses the existing script on disk.",
    )

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            for item in v:
                validate_identifier(item, "filters item")
        return v

    @field_validator("script")
    @classmethod
    def valid_python(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            compile(v, "<interceptor_script>", "exec")
        except SyntaxError as e:
            raise ValueError(f"Script is not valid Python: {e}") from e
        return v
