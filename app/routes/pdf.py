import json

from celery.result import AsyncResult
from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse

from app.broker.worker import celery_app
from app.publishers import event_consumer, task_publisher
from app.routes.dependencies import AnonymDep, PDFServiceDep, UserDep
from app.schemas.contracts import PdfRequest
from config import settings

router = APIRouter(prefix="/api/pdf", tags=["pdf"])


@router.post("/generate_tour", status_code=202)
async def generate_pdf(
    request: PdfRequest,
    user_id: AnonymDep,
):
    request.user_id = user_id
    result = await task_publisher.generate_tour_pdf(request.model_dump(mode="json"))
    return {
        "request_id": result.request_id,
        "status": "pending",
    }


@router.get("status_pdf/{request_id}")
async def get_status(request_id: str):
    task = AsyncResult(request_id, app=celery_app)
    status = task.state
    response = {"request_id": request_id, "status": status}
    if status == "SUCCESS":
        url = f"{settings.url_prefix}api/pdf/download/{request_id}"
        response["url"] = url
    if status == "FAILURE":
        response["reason"] = str(task.result) if task.result else "Unknown error"
    return response


@router.get("/events/{request_id}")
async def pdf_events(request_id: str):
    """SSE-поток для ожидания результата генерации PDF.
    Открывается сразу после отправки заявки на генерацию.
    Сервер слушает Redis Pub/Sub канал `pdf.task_updates:{request_id}` и
    отправляет данные, как только воркер завершит работу."""

    async def event_generator():
        result = await event_consumer.wait_for_result(request_id)
        if result is None:
            yield f"data: {json.dumps({'status': 'failed', 'reason': 'timeout'})}\n\n"
        else:
            yield f"data: {json.dumps(result)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Encoding": "identity",
        },
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
