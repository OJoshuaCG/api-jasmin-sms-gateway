from fastapi import APIRouter

from app.controllers.smpp_connectors_controller import SmppConnectorsController
from app.schemas.smpp_connectors import (
    SmppConnectorCreate,
    SmppConnectorOut,
    SmppConnectorStatusOut,
    SmppConnectorUpdate,
)
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/smpp-connectors", tags=["SMPP Connectors"])


@router.get("/", response_model=ApiResponse[list[SmppConnectorOut]])
async def list_connectors():
    return success(data=await SmppConnectorsController().list_connectors())


@router.get("/{cid}", response_model=ApiResponse[SmppConnectorOut])
async def get_connector(cid: str):
    return success(data=await SmppConnectorsController().get_connector(cid))


@router.post("/", response_model=ApiResponse[SmppConnectorOut], status_code=201)
async def create_connector(body: SmppConnectorCreate):
    return success(data=await SmppConnectorsController().create_connector(body), message="Connector created")


@router.patch("/{cid}", response_model=ApiResponse[SmppConnectorOut])
async def update_connector(cid: str, body: SmppConnectorUpdate):
    return success(data=await SmppConnectorsController().update_connector(cid, body))


@router.delete("/{cid}", response_model=ApiResponse[None])
async def delete_connector(cid: str):
    await SmppConnectorsController().delete_connector(cid)
    return empty("Connector deleted")


@router.post("/{cid}/start", response_model=ApiResponse[SmppConnectorStatusOut])
async def start_connector(cid: str):
    return success(data=await SmppConnectorsController().start_connector(cid), message="Connector started")


@router.post("/{cid}/stop", response_model=ApiResponse[SmppConnectorStatusOut])
async def stop_connector(cid: str):
    return success(data=await SmppConnectorsController().stop_connector(cid), message="Connector stopped")


@router.get("/{cid}/status", response_model=ApiResponse[SmppConnectorStatusOut])
async def get_connector_status(cid: str):
    return success(data=await SmppConnectorsController().get_connector_status(cid))
