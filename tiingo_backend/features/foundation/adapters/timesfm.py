from config import get_settings
from features.foundation.adapters.base import ForecastResult


class TimesFmAdapter:
    adapter_id = "timesfm"

    def __init__(self, checkpoint: str) -> None:
        self._checkpoint = checkpoint
        self._model = None

    def load(self) -> None:
        if self._model is not None:
            return
        import timesfm

        settings = get_settings()
        device = settings.foundation_device
        self._model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
            self._checkpoint,
            torch_compile=device != "cpu",
        )
        max_context = min(1024, int(settings.foundation_max_context))
        max_horizon = min(256, int(settings.foundation_max_horizon))
        self._model.compile(
            timesfm.ForecastConfig(
                max_context=max_context,
                max_horizon=max_horizon,
                normalize_inputs=True,
                use_continuous_quantile_head=True,
                force_flip_invariance=True,
                infer_is_positive=False,
                fix_quantile_crossing=True,
            )
        )

    def forecast(self, context: list[float], horizon: int) -> ForecastResult:
        import numpy as np

        if self._model is None:
            self.load()
        array = np.asarray(context, dtype=np.float32)
        point_batch, quantile_batch = self._model.forecast(
            horizon=horizon,
            inputs=[array],
        )
        point = [float(x) for x in point_batch[0][:horizon]]
        lower = upper = None
        if quantile_batch is not None and len(quantile_batch) > 0:
            q = quantile_batch[0]
            if q.shape[-2] >= 2:
                lower = [float(x) for x in q[0, :horizon]]
                upper = [float(x) for x in q[-1, :horizon]]
        return ForecastResult(point=point, lower=lower, upper=upper)
