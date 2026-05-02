from fastapi import APIRouter

from app.controllers.interceptors_controller import MoInterceptorsController
from app.schemas.interceptors import InterceptorOut, MoInterceptorCreate, MoInterceptorUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/mo-interceptors", tags=["MO Interceptors"])


@router.get("/", response_model=ApiResponse[list[InterceptorOut]])
async def list_interceptors():
    return success(data=await MoInterceptorsController().list_interceptors())


@router.get("/{order}", response_model=ApiResponse[InterceptorOut])
async def get_interceptor(order: int):
    return success(data=await MoInterceptorsController().get_interceptor(order))


@router.post("/", response_model=ApiResponse[InterceptorOut], status_code=201)
async def create_interceptor(body: MoInterceptorCreate):
    return success(data=await MoInterceptorsController().create_interceptor(body), message="MO interceptor created")


@router.patch("/{order}", response_model=ApiResponse[InterceptorOut])
async def update_interceptor(order: int, body: MoInterceptorUpdate):
    return success(data=await MoInterceptorsController().update_interceptor(order, body))


@router.delete("/flush", response_model=ApiResponse[None])
async def flush_interceptors():
    await MoInterceptorsController().flush_interceptors()
    return empty("All MO interceptors flushed")


@router.delete("/{order}", response_model=ApiResponse[None])
async def delete_interceptor(order: int):
    await MoInterceptorsController().delete_interceptor(order)
    return empty("MO interceptor deleted")
