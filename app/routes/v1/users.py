from fastapi import APIRouter

from app.controllers.users_controller import UsersController
from app.schemas.users import UserCreate, UserOut, UserStatusUpdate, UserUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=ApiResponse[list[UserOut]])
async def list_users():
    return success(data=await UsersController().list_users())


@router.get("/{uid}", response_model=ApiResponse[UserOut])
async def get_user(uid: str):
    return success(data=await UsersController().get_user(uid))


@router.post("/", response_model=ApiResponse[UserOut], status_code=201)
async def create_user(body: UserCreate):
    return success(data=await UsersController().create_user(body), message="User created")


@router.patch("/{uid}", response_model=ApiResponse[UserOut])
async def update_user(uid: str, body: UserUpdate):
    return success(data=await UsersController().update_user(uid, body))


@router.delete("/{uid}", response_model=ApiResponse[None])
async def delete_user(uid: str):
    await UsersController().delete_user(uid)
    return empty("User deleted")


@router.patch("/{uid}/status", response_model=ApiResponse[UserOut])
async def update_user_status(uid: str, body: UserStatusUpdate):
    return success(data=await UsersController().update_user_status(uid, body))
