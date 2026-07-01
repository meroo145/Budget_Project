# ai/model_loader.py
"""
Singleton loader for the trained transaction-categorization model.

WHY THIS FILE EXISTS:
  Loading a joblib model involves disk I/O + deserialization, which is slow
  (tens to hundreds of ms). Doing that inside a Django view means EVERY
  request pays that cost again. This module loads the model bundle exactly
  once per process (cached in a module-level variable) and every subsequent
  call reuses the same in-memory object.

  Budget/apps.py calls get_predictor() once from AppConfig.ready(), so the
  model is already warm in memory by the time the first real request comes
  in — not lazily loaded on the first user's request (which would make
  exactly one unlucky user experience the slow load).

WHERE THE MODEL FILE LIVES:
  <BASE_DIR>/ai/model_bundle.pkl  (i.e. the same "ai" folder as this file).
  This matches the output path used by the updated train.py.
"""

import os
import logging
import pandas as pd
from django.conf import settings

logger = logging.getLogger(__name__)

_bundle = None  # module-level cache: {"model": ..., "feature_builder": ...}


def get_predictor():
    """
    Returns the cached {"model", "feature_builder"} bundle, loading it
    from disk on first call only. Raises FileNotFoundError if the model
    hasn't been trained yet — callers should catch this and degrade
    gracefully (no suggestion shown) rather than crash the page.
    """
    global _bundle

    if _bundle is None:
        import joblib

        model_path = os.path.join(settings.BASE_DIR, 'ai', 'model_bundle.pkl')

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"No trained model found at {model_path}. "
                f"Run train.py first to generate model_bundle.pkl."
            )

        _bundle = joblib.load(model_path)
        logger.info("ML category model loaded into memory from %s", model_path)

    return _bundle


def predict_category_with_confidence(description: str, amount: float, tx_type: str):
    """
    Returns (predicted_label: str, confidence: float in [0, 1]).

    Uses predict_proba so the frontend can show a confidence percentage
    and we can decide (client-side) whether a suggestion is worth
    auto-applying vs. just displaying as a hint.
    """
    bundle = get_predictor()
    model = bundle['model']
    feature_builder = bundle['feature_builder']

    if tx_type not in ('income', 'expense'):
        tx_type = 'expense'  # safe default for a type the model never saw

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
