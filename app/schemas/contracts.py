from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Route(BaseModel):
    from_place: str = Field(..., description="Город отправления")
    to_place: str = Field(..., description="Город назначения")


class Dates(BaseModel):
    date_from: date
    date_to: date


class Accommodation(BaseModel):
    name: str = Field(..., description="Название отеля для отображения")
    partner_url: str | None = Field(
        None, description="Ссылка на партнёра (Яндекс Путешествия)"
    )


class TransferType(str, Enum):
    NEEDED = "needed"
    SELF = "self"
    OWN_CAR = "own_car"


class Transfer(BaseModel):
    type: TransferType
    parking_needed: bool | None = Field(
        None, description="Только для OWN_CAR: нужна ли парковка"
    )


class Travelers(BaseModel):
    adults: int | None = Field(None, ge=0)
    children: int | None = Field(None, ge=0)
    group_ski_level: str


class Accessibility(BaseModel):
    barrier_free: bool = False
    ramps_and_lifts: bool = False
    adapted_accommodation: bool = False


class Comfort(BaseModel):
    low_physical_load: bool = False
    calm_slopes: bool = False
    infrastructure_nearby: bool = False


class Support(BaseModel):
    escort: bool = False
    equipment_help: bool = False
    personal_instructor: bool = False


class AdditionalOptions(BaseModel):
    accessibility: Accessibility = Accessibility()
    comfort: Comfort = Comfort()
    support: Support = Support()


class Price(BaseModel):
    tickets: int | None = None
    accommodation: int | None = None
    transfer: int | None = None
    total: int


class TourPdfPayload(BaseModel):
    """Содержимое PDF для одного тура."""

    route: Route | None = None
    dates: Dates | None = None
    activity: list[str] | None = None
    accommodation: Accommodation | None = None
    transfer: Transfer | None = None
    travelers: Travelers | None = None
    additional_options: AdditionalOptions | None = None
    price: Price | None = None

    @model_validator(mode="after")
    def check_at_leats_one_param(self):
        check_fields = [
            self.route,
            self.dates,
            self.activity,
            self.accommodation,
            self.transfer,
            self.travelers,
            self.price,
        ]
        if not any(check_fields):
            raise ValueError("At least one parameter requireed.")
        return self


class PdfRequest(BaseModel):
    request_id: str
    template_id: str = "tour"
    user_id: int | None = None
    payload: TourPdfPayload
    callback: dict | None = None
