# Docker GPU for Tiingo backend

Enable NVIDIA GPU inside Docker for **`tiingo_backend`** and **`tiingo_worker_heavy`** so `FOUNDATION_DEVICE=cuda` and `SENTIMENT_DEVICE=cuda` can use the GPU (Chronos, TimesFM, FinBERT).

`tiingo_worker` (light queue) and the frontend stay CPU-only.

## Prerequisites (host)

1. NVIDIA drivers working (`nvidia-smi` on the host).
2. [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed and configured for Docker.
3. Verify toolkit:

   ```bash
   docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi
   ```

## Configure `.env`

```env
# RTX 50-series (Blackwell, sm_120): use cu128 or cu128-nightly — NOT cu124/cu126
DOCKER_TORCH_CUDA=cu128-nightly

FOUNDATION_MODELS_ENABLED=true
FOUNDATION_DEVICE=cuda

# Optional, if sentiment jobs are enabled:
SENTIMENT_DEVICE=cuda
```

| `DOCKER_TORCH_CUDA` | Use case |
|---------------------|----------|
| `cpu` | Default; no GPU / CI |
| `cu128` | Stable PyTorch with CUDA 12.8 (sm_120 on RTX 50-series) |
| `cu128-nightly` | Nightly cu128 if stable cu128 still lacks sm_120 kernels |
| `cu124` / `cu126` | Older GPUs only (Ada/Hopper). **Fails on RTX 5060** with `no kernel image` |

**VRAM:** Backend and heavy worker share one GPU. On ~8 GB cards, stop other GPU consumers (e.g. vLLM) before long foundation backtests.

## Build and run with GPU

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml build tiingo_backend tiingo_worker_heavy
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d tiingo_backend tiingo_worker_heavy
```

Rebuild all backend images when changing `DOCKER_TORCH_CUDA` (`tiingo_worker` uses the same Dockerfile).

## Verify CUDA inside containers

**1. Device visible:**

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml exec tiingo_worker_heavy python -c "import torch; print('heavy', torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```

**2. Kernels actually run (required for RTX 50-series):**

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml exec tiingo_worker_heavy python -c "
import torch
print('arch list', torch.cuda.get_arch_list())
x = torch.randn(512, 512, device='cuda')
print('matmul ok', (x @ x)[0, 0].item())
"
```

Expected: `sm_120` in arch list (or no sm_120 warning), and `matmul ok` with a numeric result — not `no kernel image`.

**3. During a foundation job:** run `watch -n 1 nvidia-smi` on the host; you should see `python` using VRAM and GPU-Util spikes.

## CPU-only hosts (default)

Omit `docker-compose.gpu.yml` and leave `DOCKER_TORCH_CUDA=cpu` (or unset). Standard `docker compose up` works without the NVIDIA toolkit.

## What uses the GPU

| Component | `FOUNDATION_DEVICE=cuda` | Notes |
|-----------|--------------------------|--------|
| Chronos | Yes | `device_map=cuda` when CUDA available |
| TimesFM | Yes | Model moved to `cuda:0` after load |
| FinBERT | `SENTIMENT_DEVICE` ≠ `cpu` | Heavy queue `news_sentiment` jobs |
| ML sklearn / LSTM / RL | No | Still CPU unless extended in code |

See also [FOUNDATION_MANUAL.md](../FOUNDATION_MANUAL.md).
