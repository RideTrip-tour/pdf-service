import asyncio
import json

from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse

from app.schemas.contracts import PdfRequest
from app.routes.query_params import PDFServiceDep, UserDep, AnonymDep
from app.redis.tasks import generate_pdf_task
from app.redis.redis import async_redis


router = APIRouter(prefix="/api/pdf", tags=["pdf"])


@router.post("/generate_tour", status_code=202)
def generate_pdf(
    request: PdfRequest,
    user_id: AnonymDep,
):
    request.user_id = user_id
    generate_pdf_task.delay(request.model_dump())
    return {"request_id": request.request_id, "status": "pending"}


@router.get("/events/{request_id}")
async def pdf_events(request_id: str):
    async def event_generator():
        pubsub = async_redis.pubsub()
        await pubsub.subscribe(f"task_updates:{request_id}")
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = message["data"]
                yield f"data: {data}\n\n"
                parsed = json.loads(data)
                if parsed.get("status") in ["ready", "failed"]:
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
