from unittest.mock import MagicMock, patch

from features.foundation.adapters.timesfm import (
    apply_foundation_torch_device,
    load_timesfm_model,
)


def test_apply_foundation_torch_device_cpu_skips_move():
    model = MagicMock()
    result = apply_foundation_torch_device(model, foundation_device="cpu")
    assert result is model
    model.to.assert_not_called()


def test_apply_foundation_torch_device_cuda_when_available():
    model = MagicMock()
    moved = MagicMock()
    model.to.return_value = moved
    with patch("torch.cuda.is_available", return_value=True):
        result = apply_foundation_torch_device(model, foundation_device="cuda")
    model.to.assert_called_once_with("cuda:0")
    assert result is moved


def test_apply_foundation_torch_device_cuda_unavailable():
    model = MagicMock()
    with patch("torch.cuda.is_available", return_value=False):
        result = apply_foundation_torch_device(model, foundation_device="cuda")
    assert result is model
    model.to.assert_not_called()


def test_load_timesfm_model_uses_from_pretrained_bypass():
    mock_model = MagicMock()
    with patch(
        "timesfm.timesfm_2p5.timesfm_2p5_torch.TimesFM_2p5_200M_torch._from_pretrained",
        return_value=mock_model,
    ) as from_pretrained:
        result = load_timesfm_model(
            "google/timesfm-2.5-200m-pytorch",
            torch_compile=False,
            cache_dir="/tmp/hf",
        )

    assert result is mock_model
    from_pretrained.assert_called_once_with(
        model_id="google/timesfm-2.5-200m-pytorch",
        revision=None,
        cache_dir="/tmp/hf",
        force_download=False,
        local_files_only=False,
        token=None,
        config=None,
        torch_compile=False,
    )
