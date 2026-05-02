from fastapi import APIRouter

from app.controllers.filters_controller import FiltersController
from app.schemas.filters import FilterCreate, FilterOut, FilterUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/filters", tags=["Filters"])


@router.get("/", response_model=ApiResponse[list[FilterOut]])
async def list_filters():
    return success(data=await FiltersController().list_filters())


@router.get("/{fid}", response_model=ApiResponse[FilterOut])
async def get_filter(fid: str):
    return success(data=await FiltersController().get_filter(fid))


@router.post("/", response_model=ApiResponse[FilterOut], status_code=201)
async def create_filter(body: FilterCreate):
    return success(data=await FiltersController().create_filter(body), message="Filter created")


@router.patch("/{fid}", response_model=ApiResponse[FilterOut])
async def update_filter(fid: str, body: FilterUpdate):
    return success(data=await FiltersController().update_filter(fid, body))


@router.delete("/{fid}", response_model=ApiResponse[None])
async def delete_filter(fid: str):
    await FiltersController().delete_filter(fid)
    return empty("Filter deleted")
