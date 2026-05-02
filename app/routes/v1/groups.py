from fastapi import APIRouter

from app.controllers.groups_controller import GroupsController
from app.schemas.groups import GroupCreate, GroupOut, GroupUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.get("/", response_model=ApiResponse[list[GroupOut]])
async def list_groups():
    return success(data=await GroupsController().list_groups())


@router.get("/{gid}", response_model=ApiResponse[GroupOut])
async def get_group(gid: str):
    return success(data=await GroupsController().get_group(gid))


@router.post("/", response_model=ApiResponse[GroupOut], status_code=201)
async def create_group(body: GroupCreate):
    return success(data=await GroupsController().create_group(body), message="Group created")


@router.patch("/{gid}", response_model=ApiResponse[GroupOut])
async def update_group(gid: str, body: GroupUpdate):
    return success(data=await GroupsController().update_group(gid, body))


@router.delete("/{gid}", response_model=ApiResponse[None])
async def delete_group(gid: str):
    await GroupsController().delete_group(gid)
    return empty("Group deleted")
