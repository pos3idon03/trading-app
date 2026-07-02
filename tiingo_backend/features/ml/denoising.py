"""Causal signal denoising for price series."""

from __future__ import annotations

from typing import Optional


def kalman_smooth_1d(values: list[float], process_var: float = 1e-5) -> list[float]:
    if not values:
        return []
    estimate = values[0]
    estimate_error = 1.0
    smoothed: list[float] = []
    for obs in values:
        prediction_error = estimate_error + process_var
        kalman_gain = prediction_error / (prediction_error + 1.0)
        estimate = estimate + kalman_gain * (obs - estimate)
        estimate_error = (1.0 - kalman_gain) * prediction_error
        smoothed.append(estimate)
    return smoothed


def _wavelet_denoise_segment(values: list[float], wavelet: str = "db4") -> list[float]:
    if len(values) < 4:
        return list(values)
    try:
        import pywt
    except ImportError:
        return list(values)

    coeffs = pywt.wavedec(values, wavelet, mode="symmetric")
    coeffs[1] = pywt.threshold(coeffs[1], value=0.04, mode="soft")
    for index in range(2, len(coeffs)):
        coeffs[index] = pywt.threshold(coeffs[index], value=0.04, mode="soft")
    reconstructed = pywt.waverec(coeffs, wavelet, mode="symmetric")
    return [float(reconstructed[index]) for index in range(len(values))]


def wavelet_denoise_causal_1d(
    values: list[float],
    *,
    window: int = 64,
    wavelet: str = "db4",
) -> list[float]:
    """Denoise each point using only a trailing window (no future leakage)."""
    if len(values) < 4:
        return list(values)

    window = max(4, window)
    denoised: list[float] = []
    for index in range(len(values)):
        start = max(0, index - window + 1)
        segment = values[start : index + 1]
        if len(segment) < 4:
            denoised.append(values[index])
            continue
        segment_denoised = _wavelet_denoise_segment(segment, wavelet=wavelet)
        denoised.append(segment_denoised[-1])
    return denoised


def wavelet_denoise_1d(values: list[float], wavelet: str = "db4") -> list[float]:
    return wavelet_denoise_causal_1d(values, wavelet=wavelet)


def denoise_series(
    values: list[float],
    method: str = "none",
) -> list[float]:
    if method == "kalman":
        return kalman_smooth_1d(values)
    if method == "wavelet":
        return wavelet_denoise_causal_1d(values)
    return list(values)


def denoised_return(closes: list[float], index: int, lookback: int) -> Optional[float]:
    if index < lookback or closes[index - lookback] == 0:
        return None
    return (closes[index] / closes[index - lookback]) - 1.0
