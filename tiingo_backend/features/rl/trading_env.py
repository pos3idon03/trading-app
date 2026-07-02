"""Gymnasium-compatible single-symbol trading environment."""

from __future__ import annotations

import math
from dataclasses import dataclass

from features.backtesting.metrics import bars_per_year
from features.rl.reward import (
    episode_sharpe_bonus,
    ewma_variance,
    mean_variance_reward,
    sharpe_annual_step_reward,
)
from features.rl.state_builder import StateBuilder


@dataclass
class TradingEnvConfig:
    state_window: int = 32
    risk_aversion_lambda: float = 2.0
    risk_vol_span: int = 20
    commission_bps: float = 5.0
    slippage_bps: float = 0.0
    action_position_pct: float = 100.0
    reward_clip: float = 0.05
    initial_cash: float = 10_000.0
    reward_mode: str = "sharpe_annual"
    decision_timeframe: str = "1d"
    asset_type: str = "equity"
    episode_sharpe_bonus_weight: float = 0.1


class TradingEnv:
    # Feedback mapping: Hold=0, Buy=1, Sell=2 (internal indices)
    ACTION_HOLD = 0
    ACTION_BUY = 1
    ACTION_SELL = 2
    ACTION_ENTER = ACTION_BUY
    ACTION_EXIT = ACTION_SELL

    def __init__(
        self,
        bars: list[dict],
        config: TradingEnvConfig | None = None,
        state_builder: StateBuilder | None = None,
    ) -> None:
        self.bars = bars
        self.config = config or TradingEnvConfig()
        self.state_builder = state_builder or StateBuilder(
            state_window=self.config.state_window,
        )
        self.index = 0
        self.cash = self.config.initial_cash
        self.shares = 0.0
        self.entry_price = 0.0
        self.peak_equity = self.config.initial_cash
        self.position_age = 0
        self._returns_history: list[float] = []
        self._annualization = bars_per_year(
            self.config.decision_timeframe,
            asset_type=self.config.asset_type,
        )

    def reset(self, start_index: int | None = None) -> list[float]:
        self.index = start_index or self.config.state_window
        self.cash = self.config.initial_cash
        self.shares = 0.0
        self.entry_price = 0.0
        self.peak_equity = self.config.initial_cash
        self.position_age = 0
        self._returns_history = []
        return self._obs()

    def valid_actions(self) -> list[int]:
        if self.shares > 0:
            return [self.ACTION_HOLD, self.ACTION_SELL]
        return [self.ACTION_HOLD, self.ACTION_BUY]

    def step(self, action: int) -> tuple[list[float], float, bool, dict]:
        if action not in self.valid_actions():
            action = self.ACTION_HOLD

        prev_equity = self._equity(self.index)
        bar = self.bars[self.index]
        price = float(bar["open"])
        turnover_cost = 0.0
        commission_drag = 0.0

        if action == self.ACTION_BUY and self.shares <= 0 and price > 0:
            budget = self.cash * (self.config.action_position_pct / 100.0)
            cost_factor = 1.0 + self.config.slippage_bps / 10_000.0
            fill = price * cost_factor
            commission = budget * (self.config.commission_bps / 10_000.0)
            spendable = max(budget - commission, 0.0)
            self.shares = spendable / fill
            self.cash -= commission + spendable
            self.entry_price = fill
            self.position_age = 0
            turnover_cost = commission / max(prev_equity, 1.0)
            commission_drag = turnover_cost

        elif action == self.ACTION_SELL and self.shares > 0 and price > 0:
            fill_factor = 1.0 - self.config.slippage_bps / 10_000.0
            fill = price * fill_factor
            notional = self.shares * fill
            commission = notional * (self.config.commission_bps / 10_000.0)
            self.cash += notional - commission
            self.shares = 0.0
            self.entry_price = 0.0
            self.position_age = 0
            turnover_cost = commission / max(prev_equity, 1.0)
            commission_drag = turnover_cost

        elif self.shares > 0:
            self.position_age += 1

        curr_equity = self._equity(self.index)
        log_ret = math.log(curr_equity / prev_equity) if prev_equity > 0 else 0.0
        self._returns_history.append(log_ret)
        trailing_var = ewma_variance(self._returns_history, self.config.risk_vol_span)
        self.peak_equity = max(self.peak_equity, curr_equity)
        dd = (curr_equity - self.peak_equity) / self.peak_equity if self.peak_equity > 0 else 0.0
        dd_penalty = max(0.0, -dd - 0.05) * 0.5

        self.index += 1
        done = self.index >= len(self.bars) - 1

        if self.config.reward_mode == "mean_variance":
            reward = mean_variance_reward(
                log_ret,
                trailing_var,
                risk_aversion_lambda=self.config.risk_aversion_lambda,
                turnover_cost=turnover_cost,
                drawdown_penalty=dd_penalty,
                reward_clip=self.config.reward_clip,
            )
        else:
            reward = sharpe_annual_step_reward(
                log_ret,
                bars_per_year=self._annualization,
                commission_drag=commission_drag,
                reward_clip=self.config.reward_clip,
            )
            if done:
                reward += episode_sharpe_bonus(
                    self._returns_history,
                    self.config.episode_sharpe_bonus_weight,
                )

        return self._obs(), reward, done, {"equity": curr_equity}

    def _equity(self, index: int) -> float:
        close = float(self.bars[index]["close"])
        return self.cash + self.shares * close

    def _obs(self) -> list[float]:
        equity = self._equity(self.index)
        close = float(self.bars[self.index]["close"])
        unrealized = 0.0
        if self.shares > 0 and self.entry_price > 0:
            unrealized = (close / self.entry_price - 1.0) * 100.0
        dd = (
            (equity - self.peak_equity) / self.peak_equity * 100.0
            if self.peak_equity > 0
            else 0.0
        )
        vol = ewma_variance(self._returns_history, self.config.risk_vol_span) ** 0.5
        return self.state_builder.build_state(
            self.bars,
            self.index,
            position_flag=1.0 if self.shares > 0 else 0.0,
            position_age=float(self.position_age),
            unrealized_pnl_pct=unrealized,
            cash_weight=self.cash / equity if equity > 0 else 1.0,
            drawdown_pct=dd,
            realized_vol=vol,
        )

    @property
    def state_dim(self) -> int:
        dummy = self.state_builder.build_state(
            self.bars,
            min(self.config.state_window, len(self.bars) - 1),
            position_flag=0.0,
            position_age=0.0,
            unrealized_pnl_pct=0.0,
            cash_weight=1.0,
            drawdown_pct=0.0,
            realized_vol=0.0,
        )
        return len(dummy)

    @property
    def n_actions(self) -> int:
        return 3
