from fastapi import APIRouter

from app.controllers.mo_routes_controller import MoRoutesController
from app.schemas.routes import MoRouteCreate, MoRouteOut, MoRouteUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/mo-routes", tags=["MO Routes"])


@router.get("/", response_model=ApiResponse[list[MoRouteOut]])
async def list_routes():
    return success(data=await MoRoutesController().list_routes())


@router.get("/{order}", response_model=ApiResponse[MoRouteOut])
async def get_route(order: int):
    return success(data=await MoRoutesController().get_route(order))


@router.post("/", response_model=ApiResponse[MoRouteOut], status_code=201)
async def create_route(body: MoRouteCreate):
    return success(data=await MoRoutesController().create_route(body), message="MO route created")


@router.patch("/{order}", response_model=ApiResponse[MoRouteOut])
async def update_route(order: int, body: MoRouteUpdate):
    return success(data=await MoRoutesController().update_route(order, body))


@router.delete("/flush", response_model=ApiResponse[None])
async def flush_routes():
    await MoRoutesController().flush_routes()
    return empty("All MO routes flushed")


@router.delete("/{order}", response_model=ApiResponse[None])
async def delete_route(order: int):
    await MoRoutesController().delete_route(order)
    return empty("MO route deleted")
