from fastapi import APIRouter

from app.controllers.http_connectors_controller import HttpConnectorsController
from app.schemas.http_connectors import HttpConnectorCreate, HttpConnectorOut, HttpConnectorUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/http-connectors", tags=["HTTP Connectors"])


@router.get("/", response_model=ApiResponse[list[HttpConnectorOut]])
async def list_connectors():
    return success(data=await HttpConnectorsController().list_connectors())


@router.get("/{cid}", response_model=ApiResponse[HttpConnectorOut])
async def get_connector(cid: str):
    return success(data=await HttpConnectorsController().get_connector(cid))


@router.post("/", response_model=ApiResponse[HttpConnectorOut], status_code=201)
async def create_connector(body: HttpConnectorCreate):
    return success(data=await HttpConnectorsController().create_connector(body), message="HTTP connector created")


@router.patch("/{cid}", response_model=ApiResponse[HttpConnectorOut])
async def update_connector(cid: str, body: HttpConnectorUpdate):
    return success(data=await HttpConnectorsController().update_connector(cid, body))


@router.delete("/{cid}", response_model=ApiResponse[None])
async def delete_connector(cid: str):
    await HttpConnectorsController().delete_connector(cid)
    return empty("HTTP connector deleted")
