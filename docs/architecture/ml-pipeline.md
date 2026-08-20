# ML pipeline: data to a served prediction

How a raw CSV becomes a risk score and a recommendation a manager can act
on, spanning Modules 6 through 10.

```mermaid
flowchart LR
    subgraph m6["Module 6 — ETL (ml/etl/)"]
        RAW["IBM HR Attrition CSV\n(Kaggle, gitignored)"]
        CLEAN["extract → validate (Pandera)\n→ clean → bootstrap+jitter augment"]
        SNAP["employee_feature_snapshots\n(offline feature store)"]
        DOMAIN["employees, salaries,\nperformance_reviews, ..."]
        RAW --> CLEAN --> SNAP
        CLEAN --> DOMAIN
    end

    subgraph m7["Module 7 — Training (ml/training/)"]
        SPLIT["StratifiedGroupKFold by lineage_id\n(no synthetic row leaks across the split)"]
        CANDIDATES["6 candidates, Optuna-tuned:\nLogReg, RF, XGBoost, LightGBM,\nCatBoost, MLP"]
        BEST["best by test ROC AUC"]
        SPLIT --> CANDIDATES --> BEST
    end

    subgraph mlflow["MLflow tracking + registry"]
        STAGING["staging alias\n(every training run)"]
        PRODUCTION["production alias\n(Module 10 promotion only)"]
    end

    subgraph m9["Module 9 — Inference (ml/inference/, backend)"]
        LOAD["load_pipeline():\nprefers production, falls back to staging"]
        EXPLAIN["ExplanationEngine (Module 8):\nSHAP + LIME + recommendations"]
        PERSIST["attrition_predictions +\nrecommendations"]
        LOAD --> EXPLAIN --> PERSIST
    end

    subgraph m10["Module 10 — Monitoring (ml/monitoring/)"]
        DRIFT["KS test (numeric) / PSI (categorical)\noldest vs. newest snapshot batch"]
        GATE{">= 3 features\ndrifted?"}
        RETRAIN["rerun Module 7's\nfull training pipeline"]
        PROMOTE{"beats whatever's\ncurrently serving?"}
        DRIFT --> GATE
        GATE -- yes --> RETRAIN --> PROMOTE
        GATE -- no --> SKIP["persist reports, stop"]
    end

    SNAP --> SPLIT
    BEST -- "register + alias" --> STAGING
    SNAP -.-> LOAD
    STAGING --> LOAD
    PRODUCTION --> LOAD
    SNAP --> DRIFT
    PROMOTE -- yes --> PRODUCTION
    PROMOTE -- no --> DISCARD["discard; production unchanged"]
```

## Why this shape

- **`employee_feature_snapshots` exists so training and inference see the
  exact same columns the same way.** Salary/performance/absence data is
  normalized into its own domain tables for the operational API, but the
  model was trained on the *raw* IBM dataset's columns (`JobLevel`,
  `OverTime`, `EnvironmentSatisfaction`, ...) — most of which have no other
  home in that normalized schema. Re-deriving them from the operational
  tables at inference time would risk silently drifting from what the
  model actually learned; snapshotting them once at ETL time doesn't.
- **`lineage_id`-grouped splits exist because bootstrap+jitter augmentation
  creates near-duplicate rows.** A plain stratified split let a synthetic
  row and its real "parent" land on opposite sides of train/test,
  inflating ROC AUC to ~0.99 by letting models partly recognize
  near-duplicates instead of learning the real pattern (see the
  [Machine Learning](../../README.md#machine-learning) section for the
  corrected ~0.78-0.80 scores).
- **Promotion requires beating the incumbent, not just finishing training.**
  Module 7's `train.py` always registers its best run under `staging` —
  that's just "the last thing that finished training," not necessarily
  good. Only Module 10's retraining path can move the `production` alias,
  and only when the new run's ROC AUC beats whichever model — production if
  one has ever been promoted, staging otherwise — is currently ahead.
