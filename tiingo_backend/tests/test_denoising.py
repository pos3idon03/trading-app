import pytest

from features.ml.denoising import denoise_series, kalman_smooth_1d


def test_kalman_smooth_reduces_noise():
    raw = [100 + ((-1) ** i) * 2 for i in range(20)]
    smoothed = kalman_smooth_1d(raw)
    assert len(smoothed) == len(raw)
    assert sum(abs(smoothed[i] - smoothed[i - 1]) for i in range(1, len(smoothed))) < sum(
        abs(raw[i] - raw[i - 1]) for i in range(1, len(raw))
    )


def test_denoise_none_passthrough():
    values = [1.0, 2.0, 3.0]
    assert denoise_series(values, "none") == values


def test_wavelet_denoise_is_causal():
    from features.ml.denoising import wavelet_denoise_causal_1d

    values = [100 + ((-1) ** index) * 2 for index in range(40)]
    full = wavelet_denoise_causal_1d(values, window=16)
    truncated = wavelet_denoise_causal_1d(values[:25], window=16)
    assert full[24] == truncated[24]
