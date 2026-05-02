from typing import Literal

from pydantic import BaseModel, Field

MtInterceptorType = Literal["DefaultInterceptor", "StaticMTInterceptor"]
MoInterceptorType = Literal["DefaultInterceptor", "StaticMOInterceptor"]


class MtInterceptorCreate(BaseModel):
    type: MtInterceptorType
    order: int = Field(..., ge=0)
    filters: list[str] = []
    script: str = Field(..., description="Python code for the interceptor script")


class MtInterceptorUpdate(BaseModel):
    filters: list[str] | None = None
    script: str | None = None


class InterceptorOut(BaseModel):
    order: int
    type: str
    filters: list[str]
    script_path: str


class MoInterceptorCreate(BaseModel):
    type: MoInterceptorType
    order: int = Field(..., ge=0)
    filters: list[str] = []
    script: str = Field(..., description="Python code for the interceptor script")


class MoInterceptorUpdate(BaseModel):
    filters: list[str] | None = None
    script: str | None = None
