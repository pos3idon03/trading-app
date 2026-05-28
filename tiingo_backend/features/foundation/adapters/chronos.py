from config import get_settings
from features.foundation.adapters.base import ForecastResult


class ChronosAdapter:
    adapter_id = "chronos"

    def __init__(self, checkpoint: str) -> None:
        self._checkpoint = checkpoint
        self._pipeline = None

    def load(self) -> None:
        if self._pipeline is not None:
            return
        import torch
        from chronos import Chronos2Pipeline

        settings = get_settings()
        device = settings.foundation_device
        device_map = "cuda" if device == "cuda" and torch.cuda.is_available() else "cpu"
        self._pipeline = Chronos2Pipeline.from_pretrained(
            self._checkpoint,
            device_map=device_map,
        )

    def forecast(self, context: list[float], horizon: int) -> ForecastResult:
        import torch

        if self._pipeline is None:
            self.load()
        tensor = torch.tensor(context, dtype=torch.float32)
        quantiles, mean = self._pipeline.predict_quantiles(
            context=tensor,
            prediction_length=horizon,
            quantile_levels=[0.1, 0.5, 0.9],
        )
        point = [float(x) for x in mean[0].tolist()[:horizon]]
        lower = [float(x) for x in quantiles[0, :, 0].tolist()[:horizon]]
        upper = [float(x) for x in quantiles[0, :, -1].tolist()[:horizon]]
        return ForecastResult(point=point, lower=lower, upper=upper)
