from dataclasses import dataclass


# extra_data={
#     "route": request.payload.route.model_dump()
#     if request.payload.route
#     else None,
#     "dates": {
#         "date_from": str(request.payload.dates.date_from)
#         if request.payload.dates
#         else None,
#         "date_to": str(request.payload.dates.date_to)
#         if request.payload.dates
#         else None,
#     }
#     if request.payload.dates
#     else None,
#     "activity": [act for act in request.payload.activity]
#     if request.payload.activity
#     else None,
# },
@dataclass(frozen=True)
class TourExtraData:
    route: dict[str, str] | None = None
    dates: dict[str, str | None] | None = None
    activity: list[str | None] | None = None

    def to_dict(self):
        return {"route": self.route, "dates": self.dates, "activity": self.activity}

    @classmethod
    def from_db(cls, raw_data: dict | None):
        if not raw_data:
            return cls
        return cls(
            route=raw_data.get("route"),
            dates=raw_data.get("dates"),
            activity=raw_data.get("activity"),
        )
