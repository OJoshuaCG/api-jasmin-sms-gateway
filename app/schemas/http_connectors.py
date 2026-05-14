from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.utils.validators import validate_identifier, validate_no_control_chars

# HTTP connectors represent outbound HTTP endpoints for MO (mobile-originated) message delivery.
# Jasmin calls these URLs when a message is received from an SMSC and matched by a MO route.
# The URL receives the message payload (source, destination, content, etc.) via GET or POST.


class HttpConnectorCreate(BaseModel):
    cid: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description=(
            "Unique connector ID. Referenced in MO routes. "
            "Only letters, digits, underscores and hyphens allowed. "
            "Example: \"webhook_crm\""
        ),
    )

    @field_validator("cid")
    @classmethod
    def validate_cid(cls, v: str) -> str:
        return validate_identifier(v, "cid")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return validate_no_control_chars(v, "url")

    url: str = Field(
        ...,
        description=(
            "Full URL that receives the MO message. Jasmin appends message params. "
            "Example: \"https://myapp.com/sms/inbound\""
        ),
    )
    method: Literal["GET", "POST"] = Field(
        ...,
        description=(
            "HTTP method Jasmin uses to deliver the message. "
            "GET: params in query string. POST: params in form body."
        ),
    )


class HttpConnectorUpdate(BaseModel):
    url: str | None = Field(default=None, description="New delivery URL.")
    method: Literal["GET", "POST"] | None = Field(default=None, description="New HTTP method.")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_no_control_chars(v, "url")
        return v


class HttpConnectorOut(BaseModel):
    cid: str
    url: str
    method: str
