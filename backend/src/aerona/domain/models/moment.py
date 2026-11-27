from dataclasses import dataclass


@dataclass(frozen=True)
class Moment:
    year: int
    season: int | None = None
    day: int | None = None
    hour: int | None = None

    def key(self) -> tuple[int, int, int, int]:
        return (self.year, self.season or 0, self.day or 0, self.hour or 0)

    def before(self, other: "Moment") -> bool:
        return self.key() < other.key()

    def at_least(self, other: "Moment | None") -> "Moment":
        if other is None or not self.before(other):
            return self
        return other if other.season is not None else Moment(other.year, self.season, self.day, self.hour)


def latest(*moments: Moment | None) -> Moment | None:
    found = [moment for moment in moments if moment is not None]
    return max(found, key=Moment.key) if found else None
