import pathlib
import sys

from sqlalchemy import select

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession


ROOT_DIR = pathlib.Path(__file__).parent.resolve()
sys.path.append(str(ROOT_DIR))

from backend.db.dependencies import get_db
from backend.db.models import TelegramUser, VideoRequest



BOT_TOKEN = "8232716158:AAELRvU_7-VjaRzg9efIp90_TPi9vjYRW6c"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

router = APIRouter()


class VideoRequestPayload(BaseModel):
    telegram_user_id: str
    type: str
    prompt: str
    image_url: str | None = None


class FalCallbackPayload(BaseModel):
    error: str | None
    gateway_request_id: str
    request_status: str
    payload: dict



tasks_status = {}


async def simulate_video(request_id: str, payload: VideoRequestPayload):

########################### Real code from Fal.ai ##############################

    # handler = await fal_client.submit_async(
    #     "fal-ai/wan-25-preview/image-to-video",
    #     arguments={
    #         "prompt": "The white dragon warrior stands still, eyes full of determination and strength. The camera slowly moves closer or circles around the warrior, highlighting the powerful presence and heroic spirit of the character.",
    #         "image_url": "https://storage.googleapis.com/falserverless/model_tests/wan/dragon-warrior.jpg"
    #     },
    # )
    #
    # async for event in handler.iter_events(with_logs=True):
    #     print(event)
    #
    # result = await handler.get()

########################### Real code from Fal.ai ##############################

    print(f"Start simulating video for {request_id}")
    await asyncio.sleep(2)

    result = {
        "error": None,
        "gateway_request_id": request_id,
        "request_status": "OK",
        "payload": {
            "video": {
                "content_type": "video/mp4",
                "file_name": f"{request_id}.mp4",
                "file_size": 2241132,
                "url": f"https://example.com/{request_id}.mp4"
            }
        }
    }
    print(f"Simulation done: {result}")


    if request_id in tasks_status:
        tasks_status[request_id]["status"] = "OK"
        tasks_status[request_id]["video_url"] = result["payload"]["video"]["url"]

    async with httpx.AsyncClient() as client:
        await client.post("http://localhost:8000/falai/sora/callback", json=result)

    return result





@router.post("/falai/sora/request")
async def create_video(request: VideoRequestPayload, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    request_id = str(uuid.uuid4())

    user = await db.execute(select(TelegramUser).where(TelegramUser.telegram_id==request.telegram_user_id))
    user = user.scalar_one_or_none()
    if not user:
        user = TelegramUser(telegram_id=request.telegram_user_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)


    video_req = VideoRequest(
        request_id=request_id,
        user_id=user.id,
        prompt_text=request.prompt
    )
    db.add(video_req)
    await db.commit()
    await db.refresh(video_req)

    tasks_status[request_id] = {"status": "pending", "video_url": None, "user": request.telegram_user_id}
    background_tasks.add_task(simulate_video, request_id, request)
    return {"request_id": request_id, "status": "processing"}


@router.post("/falai/sora/callback")
async def receive_callback(callback: FalCallbackPayload, db: AsyncSession = Depends(get_db)):
    req_id = callback.gateway_request_id
    video_url = callback.payload["video"]["url"]

    task = tasks_status.get(req_id)
    telegram_user_id = task["user"]

    video_db = await db.execute(select(VideoRequest).where(VideoRequest.request_id == req_id))
    video_db = video_db.scalar_one_or_none()
    if video_db:
        video_db.status = callback.request_status
        video_db.video_url = video_url

        await db.commit()
        await db.refresh(video_db)

    async with httpx.AsyncClient() as client:
        await client.post(
            TELEGRAM_API_URL,
            json={"chat_id": telegram_user_id, "text": f" ویدیوی شما آماده است:\n{video_url}"}
        )

    return {"message": "Callback processed and user notified"}



@router.get("/falai/sora/status/{request_id}")
async def check_status(request_id: str):
    task = tasks_status.get(request_id)
    if not task:
        return {"request_id": request_id, "status": "not_found", "video_url": None}
    return {
        "request_id": request_id,
        "status": task["status"],
        "video_url": task["video_url"]
    }
