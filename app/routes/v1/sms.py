from fastapi import APIRouter, Query

from app.controllers.sms_controller import SmsController
from app.schemas.sms import SmsBinaryRequest, SmsBalanceOut, SmsRateOut, SmsSendOut, SmsSendRequest
from app.utils.response import ApiResponse, success

router = APIRouter(prefix="/sms", tags=["SMS"])


@router.post("/send", response_model=ApiResponse[SmsSendOut])
async def send_sms(body: SmsSendRequest):
    return success(data=await SmsController().send(body))


@router.post("/send/binary", response_model=ApiResponse[SmsSendOut])
async def send_binary_sms(body: SmsBinaryRequest):
    return success(data=await SmsController().send_binary(body))


@router.get("/rate", response_model=ApiResponse[SmsRateOut])
async def get_rate(
    username: str = Query(...),
    password: str = Query(...),
    to: str = Query(...),
    sender: str | None = Query(default=None, alias="from"),
    content: str | None = Query(default=None),
):
    return success(data=await SmsController().rate(username, password, to, sender, content))


@router.get("/balance", response_model=ApiResponse[SmsBalanceOut])
async def get_balance(
    username: str = Query(...),
    password: str = Query(...),
):
    return success(data=await SmsController().balance(username, password))
