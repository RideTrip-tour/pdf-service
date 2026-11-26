from dataclasses import dataclass


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
