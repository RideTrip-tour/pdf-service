from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.crud.pdf_history import (
    get_pdf_by_request_id,
    save_pdf_history,
    search_user_history,
)
from app.dependencies.auth import get_current_user_id, get_optional_user_id
from app.routes.api import router
from app.schemas.contracts import (
    Accommodation,
    Dates,
    PdfRequest,
    Route,
    TourPdfPayload,
    Travelers,
)
from app.service.pdf import PDFService, get_pdf_service
from app.service.renderer import render_tour_pdf
from app.service.sanitize import sanitize_payload, sanitize_string
from app.service.save import process_message
from main import app


class FakeSession:
    def __init__(self):
        self.added_objects = []
        self.commits = 0

    def add(self, obj):
        self.added_objects.append(obj)

    def commit(self):
        self.commits += 1

    def execute(self, statement):
        raise AssertionError("FakeSession.execute должен быть замокан")


def test_save_guest_history_skipped():
    session = FakeSession()
    request = PdfRequest(
        request_id="guest-1",
        user_id=None,
        payload=TourPdfPayload(route=Route(from_place="A", to_place="B")),
    )

    save_pdf_history(session, request, b"fake pdf")

    assert len(session.added_objects) == 1
    assert session.commits == 1


def test_save_user_history():
    session = FakeSession()
    request = PdfRequest(
        request_id="user-1",
        user_id=42,
        payload=TourPdfPayload(
            route=Route(from_place="Москва", to_place="Сочи"),
            dates=Dates(date_from=date(2025, 1, 1), date_to=date(2025, 1, 10)),
        ),
    )

    save_pdf_history(session, request, b"fake pdf")

    assert len(session.added_objects) == 1
    assert session.commits == 1

    record = session.added_objects[0]
    assert record.user_id == 42
    assert record.from_place == "Москва"
    assert record.date_from == date(2025, 1, 1)


def test_process_message_calls_render_and_save(monkeypatch):
    session = MagicMock()
    request = PdfRequest(
        request_id="test-1",
        user_id=1,
        payload=TourPdfPayload(route=Route(from_place="A", to_place="B")),
    )

    mock_render = MagicMock(return_value=b"fake pdf")
    mock_save = MagicMock()

    monkeypatch.setattr("app.service.save.render_tour_pdf", mock_render)
    monkeypatch.setattr("app.service.save.save_pdf_history", mock_save)

    process_message(session, request)

    mock_render.assert_called_once()
    mock_save.assert_called_once_with(session, request, b"fake pdf")


def test_sanitize_payload_handles_none(monkeypatch):
    payload = TourPdfPayload.model_construct(route=None)
    result = sanitize_payload(payload)
    assert result.route is None


def test_empty_payload_raises_error():
    with pytest.raises(ValidationError) as exc_info:
        PdfRequest(request_id="test", payload=TourPdfPayload())
    assert "At least one parameter requireed" in str(exc_info.value)


def test_one_param_is_valid():
    payload = TourPdfPayload(route=Route(from_place="Москва", to_place="Сочи"))
    request = PdfRequest(request_id="test", payload=payload)
    assert request.request_id == "test"


def test_get_pdf_by_request_id_returns_none_when_missing(monkeypatch):
    session = FakeSession()

    def fake_execute(statement):
        return SimpleNamespace(scalar_one_or_none=lambda: None)

    monkeypatch.setattr(session, "execute", fake_execute)

    result = get_pdf_by_request_id(session, "non-existent-id")
    assert result is None


def test_get_pdf_by_request_id_returns_object(monkeypatch):
    session = FakeSession()
    fake_pdf = SimpleNamespace(request_id="test-1", file_data=b"pdf")

    def fake_execute(statement):
        return SimpleNamespace(scalar_one_or_none=lambda: fake_pdf)

    monkeypatch.setattr(session, "execute", fake_execute)

    result = get_pdf_by_request_id(session, "test-1")
    assert result == fake_pdf
    assert result.file_data == b"pdf"


def test_search_user_history_no_filters(monkeypatch):
    session = FakeSession()
    captured = {}

    def fake_execute(statement):
        captured["sql"] = str(statement.compile(dialect=postgresql.dialect()))
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=list))

    monkeypatch.setattr(session, "execute", fake_execute)

    search_user_history(session, user_id=42)

    sql = captured["sql"]
    assert "user_pdf_history.user_id = " in sql
    assert "user_pdf_history.from_place = " not in sql
    assert "user_pdf_history.activity LIKE " not in sql


def test_search_user_history_with_filters(monkeypatch):
    session = FakeSession()
    captured = {}

    def fake_execute(statement):
        captured["sql"] = str(statement.compile(dialect=postgresql.dialect()))
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=list))

    monkeypatch.setattr(session, "execute", fake_execute)

    search_user_history(
        session,
        user_id=42,
        from_place="Москва",
        to_place="Сочи",
        activity="лыжи",
    )

    sql = captured["sql"]
    assert "user_pdf_history.user_id = " in sql
    assert "user_pdf_history.from_place = " in sql
    assert "user_pdf_history.to_place = " in sql
    assert "user_pdf_history.activity LIKE " in sql
    assert "activity" in sql


def test_search_user_history_returns_list(monkeypatch):
    session = FakeSession()
    fake_result_1 = SimpleNamespace(request_id="1")
    fake_result_2 = SimpleNamespace(request_id="2")

    def fake_execute(statement):
        return SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: [fake_result_1, fake_result_2])
        )

    monkeypatch.setattr(session, "execute", fake_execute)

    result = search_user_history(session, user_id=42)

    assert len(result) == 2
    assert result[0].request_id == "1"
    assert result[1].request_id == "2"


def make_request(user_state: dict | None) -> MagicMock:
    request = MagicMock()
    if user_state is None:
        request.state.user = None
    else:
        request.state.user = user_state
    return request


def test_get_optional_user_id_returns_id():
    request = make_request({"user_id": 42})
    assert get_optional_user_id(request) == 42


def test_get_optional_user_id_returns_none_for_guest():
    request = make_request(None)
    assert get_optional_user_id(request) is None


def test_get_optional_user_id_invalid_type():
    request = MagicMock()
    request.state.user = "invalid"
    assert get_optional_user_id(request) is None


def test_get_current_user_id_returns_id():
    request = make_request({"user_id": 42})
    assert get_current_user_id(request) == 42


def test_get_current_user_id_raises_401_for_guest():
    request = make_request(None)
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(request)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_download_pdf_raises_404_when_missing(monkeypatch):
    session = MagicMock()
    service = PDFService(session)

    monkeypatch.setattr(
        "app.service.pdf.get_pdf_by_request_id", MagicMock(return_value=None)
    )

    with pytest.raises(HTTPException) as exc_info:
        service.download_pdf("non-existent-id")
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


def test_download_pdf_returns_bytes(monkeypatch):
    session = MagicMock()
    service = PDFService(session)

    fake_file = SimpleNamespace(file_data=b"fake-pdf-bytes")
    monkeypatch.setattr(
        "app.service.pdf.get_pdf_by_request_id", MagicMock(return_value=fake_file)
    )

    result = service.download_pdf("test-id")
    assert result == b"fake-pdf-bytes"


def test_get_history_returns_list_of_dicts(monkeypatch):
    session = MagicMock()
    service = PDFService(session)

    fake_record_1 = SimpleNamespace(
        request_id="1",
        from_place="Москва",
        to_place="Сочи",
        date_from="2025-01-01",
        date_to="2025-01-10",
        activity="лыжи",
        created_at="2025-01-01",
    )

    monkeypatch.setattr(
        "app.service.pdf.search_user_history", MagicMock(return_value=[fake_record_1])
    )

    result = service.get_history(user_id=42)

    assert len(result) == 1
    assert result[0]["request_id"] == "1"
    assert result[0]["from_place"] == "Москва"
    assert "file_data" not in result[0]


def test_get_pdf_service_returns_service():
    session = MagicMock()
    service = get_pdf_service(session=session)
    assert isinstance(service, PDFService)
    assert service.session == session


def test_sanitize_string_removes_html():
    dirty = "<script>alert('xss')</script>Москва"
    clean = sanitize_string(dirty)
    assert "<script>" not in clean
    assert "Москва" in clean


def test_sanitize_payload_cleans_fields():
    payload = TourPdfPayload(
        route=Route(from_place="<script>alert(1)</script>Москва", to_place="Сочи"),
        accommodation=Accommodation(name="Отель<script>alert(1)</script>"),
        travelers=Travelers(group_ski_level="Любитель<script>alert(1)</script>"),
    )

    clean = sanitize_payload(payload)

    assert "<script>" not in clean.route.from_place
    assert "Москва" in clean.route.from_place
    assert "<script>" not in clean.accommodation.name
    assert "Отель" in clean.accommodation.name
    assert "<script>" not in clean.travelers.group_ski_level
    assert "Любитель" in clean.travelers.group_ski_level


def test_sanitize_payload_cleans_activity_list():
    payload = TourPdfPayload(
        activity=["лыжи<script>alert(1)</script>", "сноуборд<script>alert(1)</script>"]
    )
    clean = sanitize_payload(payload)

    assert "<script>" not in clean.activity[0]
    assert "лыжи" in clean.activity[0]
    assert "<script>" not in clean.activity[1]
    assert "сноуборд" in clean.activity[1]


def test_render_tour_pdf_with_empty_payload():
    payload = TourPdfPayload.model_construct()
    pdf_bytes = render_tour_pdf(payload)
    assert pdf_bytes.startswith(b"%PDF")


def test_render_tour_pdf_returns_pdf_bytes():
    payload = TourPdfPayload(route=Route(from_place="Москва", to_place="Сочи"))
    pdf_bytes = render_tour_pdf(payload)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_references_openapi_exposes_public_and_admin_paths():
    app = FastAPI()
    app.include_router(router)

    paths = app.openapi()["paths"]

    assert "/api/pdf/generate_tour" in paths
    assert "/api/pdf/events/{request_id}" in paths
    assert "/api/pdf/download/{request_id}" in paths
    assert "/api/pdf/history" in paths


client = TestClient(app)


def override_user(user_id: int | None):
    app.dependency_overrides[get_optional_user_id] = lambda: user_id


def override_service():
    mock_service = MagicMock()
    mock_service.download_pdf.return_value = b"fake pdf bytes"
    mock_service.get_history.return_value = [
        {"request_id": "1", "from_place": "Москва"}
    ]
    app.dependency_overrides[get_pdf_service] = lambda: mock_service
    return mock_service


@pytest.fixture(autouse=True)
def cleanup():
    yield
    app.dependency_overrides.clear()


def test_generate_tour_available_for_guest(monkeypatch):
    override_user(None)

    mock_delay = MagicMock()
    monkeypatch.setattr("app.routes.api.generate_pdf_task.delay", mock_delay)

    response = client.post(
        "/api/pdf/generate_tour",
        json={
            "request_id": "guest-1",
            "payload": {"route": {"from_place": "A", "to_place": "B"}},
        },
    )

    assert response.status_code == 202
    mock_delay.assert_called_once()


def test_generate_tour_available_for_user(monkeypatch):
    override_user(42)

    mock_delay = MagicMock()
    monkeypatch.setattr("app.routes.api.generate_pdf_task.delay", mock_delay)

    response = client.post(
        "/api/pdf/generate_tour",
        json={
            "request_id": "user-1",
            "payload": {"route": {"from_place": "A", "to_place": "B"}},
        },
    )

    assert response.status_code == 202
    mock_delay.assert_called_once()


def test_download_available_for_everyone():
    override_service()

    response = client.get("/api/pdf/download/some-id")

    assert response.status_code == 200
    assert response.content == b"fake pdf bytes"
    assert "application/pdf" in response.headers["content-type"]


def test_history_forbidden_for_guest():
    app.dependency_overrides[get_current_user_id] = lambda: None
    if get_current_user_id in app.dependency_overrides:
        del app.dependency_overrides[get_current_user_id]

    response = client.get("/api/pdf/history")
    assert response.status_code == 401


def test_history_available_for_user():
    override_user(42)
    override_service()
    app.dependency_overrides[get_current_user_id] = lambda: 42

    response = client.get("/api/pdf/history", headers={"X-User-ID": "42"})

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["request_id"] == "1"
