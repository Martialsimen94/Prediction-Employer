"""LIME (Local Interpretable Model-agnostic Explanations) per-instance
attribution, as a cross-check against SHAP (ml/explainability/shap_explainer.py):
a different approximation method -- a local linear surrogate fit around the
instance, vs. exact/Shapley-value attribution -- should broadly agree on
which features drive a given prediction, and material disagreement is
itself a useful diagnostic."""

import re

import numpy as np
import pandas as pd
from lime.lime_tabular import LimeTabularExplainer
from sklearn.pipeline import Pipeline

from ml.etl.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERIC_FEATURES

# LIME's `explain_instance().as_list()` describes each feature as either
# "Feature=value" (categorical) or a numeric range like "2 < Feature <= 5"
# / "Feature <= 5" / "Feature > 5" (continuous features are discretized
# into bins). Matching each known column name as a whole word recovers the
# feature regardless of which of these forms LIME picked.
_FEATURE_PATTERNS = {column: re.compile(rf"\b{re.escape(column)}\b") for column in FEATURE_COLUMNS}


def _feature_from_description(description: str) -> str:
    for column, pattern in _FEATURE_PATTERNS.items():
        if pattern.search(description):
            return column
    raise ValueError(f"Unrecognized LIME feature description: {description!r}")


class LimeExplainer:
    """Wraps a fitted (preprocess, classifier) Pipeline. LIME perturbs
    instances in the *raw* (pre-encoding) feature space, so categorical
    columns are label-encoded up front for its internal representation,
    and `predict_fn` reverses that encoding before calling the pipeline."""

    def __init__(
        self, pipeline: Pipeline, background: pd.DataFrame, *, random_state: int = 42
    ) -> None:
        self._pipeline = pipeline
        self._categories: dict[str, list[str]] = {
            column: sorted(background[column].astype(str).unique().tolist())
            for column in CATEGORICAL_FEATURES
        }
        encoded_background = self._encode(background)
        categorical_indices = [FEATURE_COLUMNS.index(c) for c in CATEGORICAL_FEATURES]

        self._explainer = LimeTabularExplainer(
            encoded_background.to_numpy(),
            feature_names=FEATURE_COLUMNS,
            categorical_features=categorical_indices,
            categorical_names={
                index: self._categories[column]
                for index, column in zip(categorical_indices, CATEGORICAL_FEATURES, strict=True)
            },
            class_names=["stayed", "left"],
            discretize_continuous=True,
            random_state=random_state,
        )

    def _encode(self, df: pd.DataFrame) -> pd.DataFrame:
        encoded = df[FEATURE_COLUMNS].copy()
        for column in CATEGORICAL_FEATURES:
            categories = self._categories[column]
            encoded[column] = encoded[column].astype(str).map(categories.index)
        return encoded

    def _decode_and_predict_proba(self, encoded_batch: np.ndarray) -> np.ndarray:
        df = pd.DataFrame(encoded_batch, columns=FEATURE_COLUMNS)
        for column in CATEGORICAL_FEATURES:
            categories = self._categories[column]
            codes = df[column].round().astype(int).clip(0, len(categories) - 1)
            df[column] = codes.map(dict(enumerate(categories)))
        df[NUMERIC_FEATURES] = df[NUMERIC_FEATURES].astype(float)
        return self._pipeline.predict_proba(df)  # type: ignore[no-any-return]

    def explain(self, x_row: pd.Series, *, num_features: int = 10) -> dict[str, float]:
        """Local feature weights for the positive (Attrition=Yes) class,
        keyed by original employee feature name."""
        encoded_row = self._encode(x_row.to_frame().T).iloc[0].to_numpy()
        explanation = self._explainer.explain_instance(
            encoded_row,
            self._decode_and_predict_proba,
            num_features=num_features,
            labels=(1,),
        )
        return {
            _feature_from_description(description): float(weight)
            for description, weight in explanation.as_list(label=1)
        }
