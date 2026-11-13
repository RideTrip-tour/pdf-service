from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.schemas.contracts import TourPdfPayload

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


def render_tour_pdf(payload: TourPdfPayload) -> bytes:
    template = env.get_template("tour_template.html")
    html = template.render(payload=payload)
    return HTML(string=html).write_pdf()
