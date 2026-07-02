import pytest

from features.ml.imbalance import maybe_smote, should_apply_smote

try:
    import imblearn  # noqa: F401

    HAS_IMBLEARN = True
except ImportError:
    HAS_IMBLEARN = False


def test_should_apply_smote_when_imbalanced():
    y_train = [0] * 18 + [1] * 2
    assert should_apply_smote(y_train, enabled=True, min_ratio=0.15)


@pytest.mark.skipif(not HAS_IMBLEARN, reason="imbalanced-learn not installed")
def test_smote_increases_minority_count():
    x_train = [[float(i), float(i * 2)] for i in range(20)]
    y_train = [0] * 18 + [1] * 2
    x_out, y_out = maybe_smote(x_train, y_train, enabled=True, min_ratio=0.15)
    assert len(y_out) > len(y_train)
    assert y_out.count(1) > 2
