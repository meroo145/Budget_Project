from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class BudgetConfig(AppConfig):
    name = 'Budget'

    def ready(self):
        """
        Preload the ML category-prediction model once, when the Django
        process starts — not on the first incoming request. This keeps
        request latency consistent (no "first user pays the slow-load
        tax") and means model_bundle.pkl is only ever deserialized once
        per worker process.

        Wrapped in try/except so a missing/untrained model never prevents
        the server from starting — the AJAX prediction endpoint simply
        returns "no suggestion" until train.py has been run.
        """
        try:
            from ai.model_loader import get_predictor
            get_predictor()
        except Exception as e:
            logger.warning(
                "ML category model not preloaded at startup (%s). "
                "Live category suggestions will be unavailable until "
                "train.py is run to produce ai/model_bundle.pkl.",
                e,
            )
