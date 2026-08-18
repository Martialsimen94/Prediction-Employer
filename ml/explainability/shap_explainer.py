"""SHAP-based per-instance feature attribution for a fitted (preprocess,
classifier) Pipeline. Computed in the model's transformed (one-hot/scaled)
feature space, then aggregated back onto the original employee feature
names, so results are directly usable in the `attrition_predictions`
table's `shap_values` / `top_features` JSON columns (see
backend/app/models/ml.py)."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import shap
from sklearn.pipeline import Pipeline

from ml.etl.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES

# The tree ensembles among our candidate models (see ml/training/models.py)
# get shap's exact, closed-form TreeExplainer. Everything else (Logistic
# Regression, the MLP) has no closed-form attribution, so they fall back to
# a generic, model-agnostic Explainer wrapping predict_proba directly --
# slower, but correct for any classifier and consistent on the same
# probability scale as TreeExplainer's `model_output="probability"`.
_TREE_MODEL_CLASSES = frozenset(
    {"RandomForestClassifier", "XGBClassifier", "LGBMClassifier", "CatBoostClassifier"}
)


@dataclass(frozen=True)
class ShapExplanation:
    base_value: float
    contributions: dict[str, float]

    @property
    def total(self) -> float:
        """base_value + sum(contributions) reconstructs the model's
        predicted probability for the positive (Attrition=Yes) class --
        a useful correctness check on the explainer itself."""
        return self.base_value + sum(self.contributions.values())


def _original_feature_name(transformed_name: str) -> str:
    """Maps a ColumnTransformer output name (e.g. "numeric__Age" or
    "categorical__Department_Sales") back to the original employee feature
    it was derived from ("Age", "Department")."""
    _, _, remainder = transformed_name.partition("__")
    if remainder in NUMERIC_FEATURES:
        return remainder
    for column in CATEGORICAL_FEATURES:
        if remainder.startswith(f"{column}_"):
            return column
    raise ValueError(f"Unrecognized transformed feature name: {transformed_name!r}")


class ShapExplainer:
    """Wraps a fitted Pipeline (see ml/etl/features.py + ml/training/models.py)
    to produce per-instance SHAP attributions in original-feature space."""

    def __init__(self, pipeline: Pipeline, background: pd.DataFrame) -> None:
        self._preprocess = pipeline.named_steps["preprocess"]
        self._classifier = pipeline.named_steps["classifier"]
        self._feature_names = list(self._preprocess.get_feature_names_out())
        background_transformed = self._preprocess.transform(background)

        if type(self._classifier).__name__ in _TREE_MODEL_CLASSES:
            self._explainer = shap.TreeExplainer(
                self._classifier, background_transformed, model_output="probability"
            )
        else:
            self._explainer = shap.Explainer(self._classifier.predict_proba, background_transformed)

    def explain(self, x: pd.DataFrame) -> list[ShapExplanation]:
        """One ShapExplanation per row of `x` (original, pre-encoding
        employee features)."""
        x_transformed = self._preprocess.transform(x)
        raw = self._explainer(x_transformed)
        values = raw.values
        base_values = raw.base_values
        # Explainers that expose both classes' contributions (TreeExplainer
        # on sklearn's RandomForest, and the generic predict_proba-wrapping
        # Explainer) return a trailing class axis -- keep the positive
        # (Attrition=Yes) class. Explainers with a single-output classifier
        # (XGBoost/LightGBM/CatBoost's TreeExplainer) already return it bare.
        if values.ndim == 3:
            values = values[:, :, 1]
            base_values = np.asarray(base_values)[:, 1]

        return [
            ShapExplanation(base_value=float(base), contributions=self._aggregate(row))
            for row, base in zip(values, base_values, strict=True)
        ]

    def _aggregate(self, row: np.ndarray) -> dict[str, float]:
        aggregated: dict[str, float] = {}
        for name, value in zip(self._feature_names, row, strict=True):
            original = _original_feature_name(name)
            aggregated[original] = aggregated.get(original, 0.0) + float(value)
        return aggregated
