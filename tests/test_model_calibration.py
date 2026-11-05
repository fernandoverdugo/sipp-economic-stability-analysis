import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calibrate_models import fit_sigmoid, logit


def test_logit_is_finite_at_probability_edges():
    values = logit(np.array([0.0, 0.5, 1.0]))
    assert np.isfinite(values).all()
    assert values.shape == (3, 1)


def test_sigmoid_calibrator_returns_probabilities():
    probabilities = np.array([0.1, 0.2, 0.7, 0.8, 0.9, 0.3])
    y = np.array([0, 0, 1, 1, 1, 0])
    weights = np.ones(len(y))

    calibrator = fit_sigmoid(probabilities, y, weights)
    calibrated = calibrator.predict_proba(logit(probabilities))[:, 1]

    assert calibrated.shape == probabilities.shape
    assert np.all((0 <= calibrated) & (calibrated <= 1))
