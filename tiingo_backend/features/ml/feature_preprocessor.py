"""Shared walk-forward feature preprocessing for training and inference."""

from __future__ import annotations

from dataclasses import dataclass, field

from features.ml.block_pca import (
    BlockPcaState,
    block_pcas_output_names,
    transform_rows_with_block_pcas,
)
from features.ml.correlation_selection import (
    apply_feature_mask,
    mask_feature_names,
    prune_correlated_features,
)
from features.ml.fundamental_pca import fit_fundamental_pca
from features.ml.macro_pca import MacroPcaBundle, fit_macro_pca
from features.ml.regime_features import (
    regime_at_index,
    resolve_enabled_indicator_groups,
    select_features_for_regime,
)
from features.ml.technical_pca import fit_technical_pca


@dataclass
class FeaturePreprocessor:
    feature_mask: list[int]
    output_feature_names: list[str]
    pruned_features: list[str] = field(default_factory=list)
    regime_meta: dict | None = None
    technical_pca: BlockPcaState | None = None
    macro_pca: MacroPcaBundle | None = None
    fundamental_pca: BlockPcaState | None = None

    def _block_pca_states(self) -> list[BlockPcaState]:
        states: list[BlockPcaState] = []
        if self.technical_pca is not None:
            states.append(self.technical_pca)
        if self.macro_pca is not None:
            states.extend(
                self.macro_pca.states[category]
                for category in sorted(self.macro_pca.states.keys())
            )
        if self.fundamental_pca is not None:
            states.append(self.fundamental_pca)
        return states

    def transform(self, rows: list[list[float]]) -> list[list[float]]:
        masked = apply_feature_mask(rows, self.feature_mask)
        block_states = self._block_pca_states()
        if block_states:
            return transform_rows_with_block_pcas(masked, block_states)
        return masked

    def transform_optional_rows(
        self,
        rows: list[list[float] | None],
    ) -> list[list[float] | None]:
        transformed: list[list[float] | None] = []
        for row in rows:
            if row is None:
                transformed.append(None)
                continue
            transformed.append(self.transform([row])[0])
        return transformed


def _compute_feature_importances(
    x_train: list[list[float]],
    y_train: list[int],
    feature_names: list[str],
) -> dict[str, float]:
    from sklearn.ensemble import RandomForestClassifier

    if len(x_train) < 2 or len(set(y_train)) < 2:
        return {name: 1.0 for name in feature_names}

    estimator_count = min(50, max(10, len(x_train) // 2))
    model = RandomForestClassifier(
        n_estimators=estimator_count,
        random_state=42,
        n_jobs=1,
        max_depth=5,
    )
    model.fit(x_train, y_train)
    return {
        name: float(importance)
        for name, importance in zip(feature_names, model.feature_importances_)
    }


def _apply_regime_selection(
    mask: list[int],
    feature_names: list[str],
    x_train: list[list[float]],
    y_train: list[int],
    params: dict,
    closes: list[float] | None,
    train_indices: list[int],
) -> tuple[list[int], dict | None]:
    if not params.get("dynamic_indicator_selection") or not closes or not train_indices:
        return mask, None

    regime = regime_at_index(closes, train_indices[-1])
    if not regime:
        return mask, None

    masked_names = mask_feature_names(feature_names, mask)
    masked_rows = apply_feature_mask(x_train, mask)
    importances = _compute_feature_importances(masked_rows, y_train, masked_names)
    enabled_groups = resolve_enabled_indicator_groups(params)
    selected = select_features_for_regime(
        masked_names,
        importances,
        regime,
        enabled_groups=enabled_groups,
    )
    selected_set = set(selected)
    refined = [index for index in mask if feature_names[index] in selected_set] or mask
    return refined, {
        "regime": regime,
        "selected": selected,
        "enabled_groups": sorted(enabled_groups),
    }


def _collect_block_pca_states(
    masked_rows: list[list[float]],
    masked_names: list[str],
    params: dict,
) -> tuple[BlockPcaState | None, MacroPcaBundle | None, BlockPcaState | None, list[str]]:
    tech_state: BlockPcaState | None = None
    if params.get("technical_pca_enabled"):
        fixed = params.get("technical_pca_n_components")
        halflife = params.get("technical_pca_ewm_halflife")
        tech_state = fit_technical_pca(
            masked_rows,
            masked_names,
            variance_threshold=float(params.get("technical_pca_variance_threshold", 0.85)),
            n_components=int(fixed) if fixed is not None else None,
            ewm_halflife=float(halflife) if halflife is not None else None,
        )

    macro_bundle = fit_macro_pca(masked_rows, masked_names, params)
    fund_state = fit_fundamental_pca(masked_rows, masked_names, params)

    block_states: list[BlockPcaState] = []
    if tech_state is not None:
        block_states.append(tech_state)
    if macro_bundle is not None:
        block_states.extend(
            macro_bundle.states[category]
            for category in sorted(macro_bundle.states.keys())
        )
    if fund_state is not None:
        block_states.append(fund_state)

    output_names = block_pcas_output_names(masked_names, block_states)
    return tech_state, macro_bundle, fund_state, output_names


def fit_feature_preprocessor(
    x_train: list[list[float]],
    y_train: list[int],
    feature_names: list[str],
    params: dict,
    *,
    closes: list[float] | None = None,
    train_indices: list[int] | None = None,
) -> FeaturePreprocessor:
    threshold = float(params.get("correlation_prune_threshold", 0.75))
    mask, pruned = prune_correlated_features(
        x_train,
        feature_names,
        threshold=threshold,
    )
    mask, regime_meta = _apply_regime_selection(
        mask,
        feature_names,
        x_train,
        y_train,
        params,
        closes,
        train_indices or [],
    )

    masked_rows = apply_feature_mask(x_train, mask)
    masked_names = mask_feature_names(feature_names, mask)
    tech_state, macro_bundle, fund_state, output_names = _collect_block_pca_states(
        masked_rows,
        masked_names,
        params,
    )

    return FeaturePreprocessor(
        feature_mask=mask,
        output_feature_names=output_names,
        pruned_features=pruned,
        regime_meta=regime_meta,
        technical_pca=tech_state,
        macro_pca=macro_bundle,
        fundamental_pca=fund_state,
    )
