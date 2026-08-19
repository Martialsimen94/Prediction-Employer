"""Module 9: ML inference — loads the trained pipeline (Module 7) from the
MLflow model registry and reconstructs model-ready feature rows from the
offline feature store (Module 6) so the backend API can score an employee
and persist a `PredictionExplanation` (Module 8) against them."""
