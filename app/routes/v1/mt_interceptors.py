from fastapi import APIRouter

from app.controllers.interceptors_controller import MtInterceptorsController
from app.schemas.interceptors import InterceptorOut, MtInterceptorCreate, MtInterceptorUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/mt-interceptors", tags=["MT Interceptors"])


@router.get("/", response_model=ApiResponse[list[InterceptorOut]])
async def list_interceptors():
    return success(data=await MtInterceptorsController().list_interceptors())


@router.get("/{order}", response_model=ApiResponse[InterceptorOut])
async def get_interceptor(order: int):
    return success(data=await MtInterceptorsController().get_interceptor(order))


@router.post("/", response_model=ApiResponse[InterceptorOut], status_code=201)
async def create_interceptor(body: MtInterceptorCreate):
    return success(data=await MtInterceptorsController().create_interceptor(body), message="MT interceptor created")


@router.patch("/{order}", response_model=ApiResponse[InterceptorOut])
async def update_interceptor(order: int, body: MtInterceptorUpdate):
    return success(data=await MtInterceptorsController().update_interceptor(order, body))


@router.delete("/flush", response_model=ApiResponse[None])
async def flush_interceptors():
    await MtInterceptorsController().flush_interceptors()
    return empty("All MT interceptors flushed")


@router.delete("/{order}", response_model=ApiResponse[None])
async def delete_interceptor(order: int):
    await MtInterceptorsController().delete_interceptor(order)
    return empty("MT interceptor deleted")
