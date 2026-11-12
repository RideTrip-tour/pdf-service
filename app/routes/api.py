import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Response
from pydantic import BaseModel
from sse_starlette import EventSourceResponse
import redis.asyncio as aioredis
from fastapi.responses import StreamingResponse

from app.schemas.contracts import PdfRequest
from app.routes.query_params import PDFServiceDep, UserDep
from app.tasks.tasks import generate_pdf_task
from app.core.redis import async_redis

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pdf", tags=["pdf"])


@router.post("/generate_tour", status_code=202)
def generate_pdf(
    request: PdfRequest,
    user_id: UserDep,
):
    request.user_id = user_id
    generate_pdf_task.delay(request.model_dump())
    return {"request_id": request.request_id, "status": "pending"}


@router.get("/events/{request_id}")
async def pdf_events(request_id: str):
    async def event_generator():
        pubsub = async_redis.pubsub()
        channel = f"task_updates:{request_id}"
        await pubsub.subscribe(channel)
        log.info(f"SSE: Подписались на {channel}")
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = message["data"]
                log.info(f"SSE: Получены данные: {data}")
                log.info("TYPE DATA: %s", type(data))
                yield f"data: {data}\n\n"
                parsed = json.loads(data)
                if parsed.get("status") in ["ready", "failed"]:
                    log.info("SSE: закрываем соединение")
                    break
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(f"task_updates:{request_id}")
            await pubsub.close()
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Encoding": "identity"
        }
    )


@router.get("/download/{request_id}")
def download_pdf(service: PDFServiceDep, request_id: str):
    file_bytes = service.download_pdf(request_id)
    return Response(
        content=file_bytes,
        media_type="application/pdf",
        headers={
            # заставляет браузер скачать файл с именем "tour_{request_id}.pdf"
            "Content-Disposition": f'attachment; filename="tour_{request_id}.pdf"'
        },
    )


@router.get("/history")
def get_history(
    service: PDFServiceDep,
    user_id: UserDep,
    from_place: str | None = None,
    to_place: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    activity: str | None = None,
):
    return service.get_history(
        user_id,
        from_place=from_place,
        to_place=to_place,
        date_from=date_from,
        date_to=date_to,
        activity=activity,
    )
