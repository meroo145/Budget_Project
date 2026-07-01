# ai/model_loader.py
"""
Singleton loader for the trained transaction-categorization model, with
automatic hot-reload when a newer model_bundle.pkl appears on disk.

WHY THIS FILE EXISTS:
  Loading a joblib model involves disk I/O + deserialization, which is slow
  (tens to hundreds of ms). Doing that inside a Django view means EVERY
  request pays that cost again. This module loads the model bundle once
  per process and reuses the same in-memory object -- but it also checks
  the file's modification time on each call (a cheap os.stat, not a
  re-read) so a freshly retrained model is picked up automatically on the
  next request, with NO server restart required.

WHERE THE MODEL FILE LIVES:
  <BASE_DIR>/ai/model_bundle.pkl  (i.e. the same "ai" folder as this file).
"""

import os
import logging
import pandas as pd
from django.conf import settings

logger = logging.getLogger(__name__)

_bundle = None           # cached {"model": ..., "feature_builder": ...}
_bundle_mtime = None      # last-loaded model_bundle.pkl modification time


def _model_path() -> str:
    return os.path.join(settings.BASE_DIR, 'ai', 'model_bundle.pkl')


def get_predictor():
    """
    Returns the cached bundle, reloading it if:
      - it has never been loaded in this process, OR
      - the file on disk has a newer modification time than what's cached
        (i.e. a retrain happened since the last load).

    Raises FileNotFoundError if no model has been trained yet -- callers
    should catch this and degrade gracefully (no suggestion shown).
    """
    global _bundle, _bundle_mtime

    model_path = _model_path()

    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"No trained model found at {model_path}. "
            f"Run `python manage.py retrain_category_model` first."
        )

    current_mtime = os.path.getmtime(model_path)

    if _bundle is None or current_mtime != _bundle_mtime:
        import joblib
        _bundle = joblib.load(model_path)
        _bundle_mtime = current_mtime
        logger.info(
            "ML category model (re)loaded into memory from %s (mtime=%s)",
            model_path, current_mtime,
        )

    return _bundle


def predict_category_with_confidence(description: str, amount: float, tx_type: str):
    """
    Returns (predicted_label: str, confidence: float in [0, 1]).
    """
    bundle = get_predictor()
    model = bundle['model']
    feature_builder = bundle['feature_builder']

    if tx_type not in ('income', 'expense'):
        tx_type = 'expense'

    df = pd.DataFrame([{
        'description': description or '',
        'amount': amount if amount is not None else 0.0,
        'type': tx_type,
    }])

    X = feature_builder.transform(df)
    proba = model.predict_proba(X)[0]
    best_idx = proba.argmax()

    label = model.classes_[best_idx]
    confidence = float(proba[best_idx])

    return label, confidence