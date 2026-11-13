from justhtml import JustHTML

from app.schemas.contracts import TourPdfPayload


def sanitize_string(text: str | None) -> str | None:
    if not text:
        return text

    doc = JustHTML(text, fragment=True)
    return doc.to_html(pretty=False)


def sanitize_payload(payload: TourPdfPayload):
    if payload.route:
        payload.route.from_place = sanitize_string(payload.route.from_place)
        payload.route.to_place = sanitize_string(payload.route.to_place)

    if payload.activity:
        payload.activity = [sanitize_string(activity) for activity in payload.activity]  # тут

    if payload.accommodation:
        payload.accommodation.name = sanitize_string(payload.accommodation.name)    # тут

    if payload.travelers:
        payload.travelers.group_ski_level = sanitize_string(    # тут
            payload.travelers.group_ski_level
        )

    return payload
