from fastapi import APIRouter

from app.controllers.mt_routes_controller import MtRoutesController
from app.schemas.routes import MtRouteCreate, MtRouteOut, MtRouteUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/mt-routes", tags=["MT Routes"])


@router.get("/", response_model=ApiResponse[list[MtRouteOut]])
async def list_routes():
    return success(data=await MtRoutesController().list_routes())


@router.get("/{order}", response_model=ApiResponse[MtRouteOut])
async def get_route(order: int):
    return success(data=await MtRoutesController().get_route(order))


@router.post("/", response_model=ApiResponse[MtRouteOut], status_code=201)
async def create_route(body: MtRouteCreate):
    return success(data=await MtRoutesController().create_route(body), message="MT route created")


@router.patch("/{order}", response_model=ApiResponse[MtRouteOut])
async def update_route(order: int, body: MtRouteUpdate):
    return success(data=await MtRoutesController().update_route(order, body))


@router.delete("/flush", response_model=ApiResponse[None])
async def flush_routes():
    await MtRoutesController().flush_routes()
    return empty("All MT routes flushed")


@router.delete("/{order}", response_model=ApiResponse[None])
async def delete_route(order: int):
    await MtRoutesController().delete_route(order)
    return empty("MT route deleted")
