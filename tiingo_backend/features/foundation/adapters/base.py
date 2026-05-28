from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ForecastResult:
    point: list[float] = field(default_factory=list)
    lower: list[float] | None = None
    upper: list[float] | None = None


class FoundationAdapter(Protocol):
    adapter_id: str

    def load(self) -> None: ...

    def forecast(self, context: list[float], horizon: int) -> ForecastResult: ...
