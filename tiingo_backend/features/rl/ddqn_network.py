"""Double DQN Q-network."""

from __future__ import annotations


def build_q_network(state_dim: int, n_actions: int, hidden: int = 128):
    torch, nn = _require_torch()

    class QNetwork(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(state_dim, hidden),
                nn.ReLU(),
                nn.Linear(hidden, hidden),
                nn.ReLU(),
                nn.Linear(hidden, n_actions),
            )

        def forward(self, x):
            return self.net(x)

    return QNetwork()


def _require_torch():
    try:
        import torch
        import torch.nn as nn
    except ImportError as exc:
        raise ImportError("DDQN requires torch") from exc
    return torch, nn
