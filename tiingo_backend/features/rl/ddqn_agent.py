"""Double Deep Q-Network agent with replay buffer."""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field

from features.rl.ddqn_network import build_q_network


@dataclass
class DdqnConfig:
    gamma: float = 0.99
    learning_rate: float = 1e-4
    batch_size: int = 64
    replay_capacity: int = 50_000
    target_sync_steps: int = 500
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay_steps: int = 10_000
    warmup_steps: int = 200
    train_freq: int = 4


@dataclass
class DdqnAgent:
    state_dim: int
    n_actions: int
    config: DdqnConfig = field(default_factory=DdqnConfig)
    steps: int = 0
    buffer: deque = field(default_factory=deque)

    def __post_init__(self) -> None:
        torch, _ = _require_torch()
        self._torch = torch
        self.online = build_q_network(self.state_dim, self.n_actions)
        self.target = build_q_network(self.state_dim, self.n_actions)
        self.target.load_state_dict(self.online.state_dict())
        self.optimizer = torch.optim.Adam(
            self.online.parameters(),
            lr=self.config.learning_rate,
        )
        self.loss_fn = torch.nn.SmoothL1Loss()

    def epsilon(self) -> float:
        cfg = self.config
        frac = min(1.0, self.steps / max(cfg.epsilon_decay_steps, 1))
        return cfg.epsilon_start + frac * (cfg.epsilon_end - cfg.epsilon_start)

    def select_action(
        self,
        state: list[float],
        valid_actions: list[int],
        explore: bool = True,
    ) -> int:
        if explore and random.random() < self.epsilon():
            return random.choice(valid_actions)
        torch = self._torch
        self.online.eval()
        with torch.no_grad():
            s = torch.tensor([state], dtype=torch.float32)
            q = self.online(s)[0].numpy()
        for a in range(len(q)):
            if a not in valid_actions:
                q[a] = float("-inf")
        return int(max(valid_actions, key=lambda a: q[a]))

    def remember(
        self,
        state: list[float],
        action: int,
        reward: float,
        next_state: list[float],
        done: bool,
        next_valid: list[int],
    ) -> None:
        self.buffer.append((state, action, reward, next_state, done, next_valid))
        if len(self.buffer) > self.config.replay_capacity:
            self.buffer.popleft()

    def train_step(self) -> float | None:
        cfg = self.config
        if len(self.buffer) < cfg.batch_size or self.steps < cfg.warmup_steps:
            return None
        if self.steps % cfg.train_freq != 0:
            return None

        batch = random.sample(self.buffer, cfg.batch_size)
        torch = self._torch
        states = torch.tensor([b[0] for b in batch], dtype=torch.float32)
        actions = torch.tensor([b[1] for b in batch], dtype=torch.long)
        rewards = torch.tensor([b[2] for b in batch], dtype=torch.float32)
        next_states = torch.tensor([b[3] for b in batch], dtype=torch.float32)
        dones = torch.tensor([b[4] for b in batch], dtype=torch.float32)

        self.online.train()
        q_values = self.online(states).gather(1, actions.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            next_q_online = self.online(next_states)
            next_actions = next_q_online.argmax(dim=1)
            next_q_target = self.target(next_states)
            max_next = next_q_target.gather(1, next_actions.unsqueeze(1)).squeeze(1)
            targets = rewards + cfg.gamma * max_next * (1.0 - dones)

        loss = self.loss_fn(q_values, targets)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.online.parameters(), 1.0)
        self.optimizer.step()

        if self.steps % cfg.target_sync_steps == 0:
            self.target.load_state_dict(self.online.state_dict())
        return float(loss.item())

    def tick(self) -> None:
        self.steps += 1


def _require_torch():
    try:
        import torch
    except ImportError as exc:
        raise ImportError("DDQN requires torch") from exc
    return torch, None
