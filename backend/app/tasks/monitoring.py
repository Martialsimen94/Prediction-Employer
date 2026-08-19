"""Scheduled drift detection + automated retraining (Module 10). Compares
the most recent `employee_feature_snapshots` batch (Module 6's ETL output)
against the oldest one on record as its reference distribution, persists
one `DataDriftReport` row per feature, and — if enough features have
drifted — retrains and promotes a new model if it beats whatever's
currently serving predictions (`ml.monitoring.retrain`)."""

import structlog
from celery import Task

from app.core.celery_app import celery_app
from app.core.db import SessionLocal
from ml.monitoring.reports import run_drift_check, snapshot_period_range
from ml.monitoring.retrain import retrain_and_promote, should_retrain

logger = structlog.get_logger()


@celery_app.task(bind=True)  # type: ignore
def check_drift_and_retrain_task(
    self: Task, *, target_rows: int = 5000, n_trials: int = 12
) -> None:
    with SessionLocal() as session:
        period_range = snapshot_period_range(session)
        if period_range is None:
            logger.info("drift_check_skipped", reason="no feature snapshots yet")
            return

        earliest, latest = period_range
        if earliest == latest:
            logger.info("drift_check_skipped", reason="only one snapshot batch on record")
            return

        reports = run_drift_check(
            session,
            reference_start=earliest,
            reference_end=earliest,
            current_start=latest,
            current_end=latest,
        )
        session.commit()
        logger.info(
            "drift_check_completed",
            drifted=sum(report.drift_detected for report in reports),
            total=len(reports),
        )

        if not should_retrain(reports):
            return

        logger.info("retraining_triggered")
        promoted = retrain_and_promote(session, target_rows=target_rows, n_trials=n_trials)
        session.commit()
        if promoted is not None:
            logger.info("model_promoted", run_id=promoted.run_id, roc_auc=promoted.result.roc_auc)
        else:
            logger.info("retrain_did_not_improve_on_serving_model")
