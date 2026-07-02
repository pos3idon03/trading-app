"""Sklearn-compatible stacked LSTM classifier."""

from __future__ import annotations

import numpy as np
from sklearn.preprocessing import StandardScaler

from features.ml.sequence_builder import build_sequences
from features.ml.sparse_event_training import effective_lstm_seq_length


class LstmClassifier:
    classes_: np.ndarray
    n_features_in_: int

    def __init__(
        self,
        *,
        seq_length: int = 32,
        hidden_size: int = 64,
        num_layers: int = 2,
        epochs: int = 10,
        dropout: float = 0.2,
        learning_rate: float = 0.001,
        batch_size: int = 32,
        early_stopping_patience: int = 3,
        validation_fraction: float = 0.15,
    ) -> None:
        self.seq_length = seq_length
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.epochs = epochs
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.early_stopping_patience = early_stopping_patience
        self.validation_fraction = validation_fraction
        self._model = None
        self._fit_seq_length: int | None = None
        self._scaler: StandardScaler | None = None
        self.classes_ = np.array([0, 1])
        self.n_features_in_ = 0

    def _require_torch(self):
        try:
            import torch
            import torch.nn as nn
        except ImportError as exc:
            raise ImportError(
                "LSTM requires torch. Install requirements-deep-learning.txt"
            ) from exc
        return torch, nn

    def _build_network(self, n_features: int):
        torch, nn = self._require_torch()
        hidden = self.hidden_size
        layers = self.num_layers
        drop = self.dropout

        class _Net(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.lstm = nn.LSTM(
                    n_features,
                    hidden,
                    layers,
                    batch_first=True,
                    dropout=drop if layers > 1 else 0.0,
                )
                self.head = nn.Linear(hidden, 2)

            def forward(self, x):
                out, _ = self.lstm(x)
                return self.head(out[:, -1, :])

        return _Net()

    def _scale_rows(self, rows: list[list[float]], *, fit: bool) -> list[list[float]]:
        matrix = np.array(rows, dtype=float)
        if fit or self._scaler is None:
            self._scaler = StandardScaler()
            scaled = self._scaler.fit_transform(matrix)
        else:
            scaled = self._scaler.transform(matrix)
        return scaled.tolist()

    def _split_train_validation(
        self,
        seqs: list[list[list[float]]],
        labels: list[int],
    ) -> tuple[list[list[list[float]]], list[int], list[list[list[float]]], list[int]]:
        if len(seqs) < 4:
            return seqs, labels, [], []

        val_count = max(1, int(len(seqs) * self.validation_fraction))
        if val_count >= len(seqs):
            val_count = max(1, len(seqs) // 5)
        split_at = len(seqs) - val_count
        if split_at < 1:
            return seqs, labels, [], []
        return (
            seqs[:split_at],
            labels[:split_at],
            seqs[split_at:],
            labels[split_at:],
        )

    def fit(self, x_train: list[list[float]], y_train: list[int]) -> "LstmClassifier":
        torch, _ = self._require_torch()
        from torch.utils.data import DataLoader, TensorDataset

        if not x_train:
            raise ValueError("x_train is empty")
        n_features = len(x_train[0])
        self.n_features_in_ = n_features
        rows = self._scale_rows([list(map(float, row)) for row in x_train], fit=True)
        fit_seq = effective_lstm_seq_length(self.seq_length, len(rows))
        self._fit_seq_length = fit_seq
        seqs, seq_indices = build_sequences(rows, fit_seq)
        if not seqs:
            raise ValueError("Insufficient rows for LSTM sequence length")

        y = [y_train[index] for index in seq_indices]
        self.classes_ = np.array(sorted(set(y)))
        train_seqs, train_y, val_seqs, val_y = self._split_train_validation(seqs, y)

        train_x = torch.tensor(train_seqs, dtype=torch.float32)
        train_y_tensor = torch.tensor(train_y, dtype=torch.long)
        loader = DataLoader(
            TensorDataset(train_x, train_y_tensor),
            batch_size=min(self.batch_size, len(train_y)),
            shuffle=True,
        )

        val_x = None
        val_y_tensor = None
        if val_seqs:
            val_x = torch.tensor(val_seqs, dtype=torch.float32)
            val_y_tensor = torch.tensor(val_y, dtype=torch.long)

        self._model = self._build_network(n_features)
        optimizer = torch.optim.Adam(self._model.parameters(), lr=self.learning_rate)
        loss_fn = torch.nn.CrossEntropyLoss()

        best_state = None
        best_val_loss = float("inf")
        patience_left = self.early_stopping_patience

        for _ in range(self.epochs):
            self._model.train()
            for batch_x, batch_y in loader:
                optimizer.zero_grad()
                logits = self._model(batch_x)
                loss = loss_fn(logits, batch_y)
                loss.backward()
                optimizer.step()

            if val_x is None or val_y_tensor is None:
                continue

            self._model.eval()
            with torch.no_grad():
                val_logits = self._model(val_x)
                val_loss = float(loss_fn(val_logits, val_y_tensor).item())
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {key: value.clone() for key, value in self._model.state_dict().items()}
                patience_left = self.early_stopping_patience
            else:
                patience_left -= 1
                if patience_left <= 0:
                    break

        if best_state is not None:
            self._model.load_state_dict(best_state)
        return self

    def predict_proba(self, x_rows: list[list[float]]) -> np.ndarray:
        torch, _ = self._require_torch()
        if self._model is None or self._scaler is None:
            raise RuntimeError("Model not fitted")

        rows = self._scale_rows([list(map(float, row)) for row in x_rows], fit=False)
        seq_len = self._fit_seq_length or self.seq_length
        seqs, seq_indices = build_sequences(rows, effective_lstm_seq_length(seq_len, len(rows)))
        full = np.full((len(x_rows), 2), 0.5)
        if not seqs:
            return full

        self._model.eval()
        with torch.no_grad():
            x_tensor = torch.tensor(seqs, dtype=torch.float32)
            logits = self._model(x_tensor)
            probs = torch.softmax(logits, dim=1).numpy()

        for idx, prob in zip(seq_indices, probs):
            full[idx] = prob
        return full

    def predict(self, x_rows: list[list[float]]) -> np.ndarray:
        proba = self.predict_proba(x_rows)
        return self.classes_[np.argmax(proba, axis=1)]
