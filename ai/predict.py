# ai/predict.py

import os
import joblib
import pandas as pd


# Load the single bundled artifact (model + fitted feature pipeline).
# Build an ABSOLUTE path from this file's location instead of a bare
# "model_bundle.pkl" relative to the current working directory -- the latter
# raised FileNotFoundError whenever the process was started from anywhere
# other than the ai/ folder (i.e. always, when run from the project root).
_BUNDLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_bundle.pkl")

_bundle = joblib.load(_BUNDLE_PATH)
model = _bundle["model"]
feature_builder = _bundle["feature_builder"]


def predict_category(description, amount, tx_type):
    """
    Predict category for a single transaction.

    Raises ValueError if inputs are missing/invalid instead of failing
    silently or crashing deep inside sklearn with an unclear traceback.
    """

    if amount is None:
        raise ValueError("amount is required")
    if tx_type not in ("income", "expense"):
        raise ValueError(f"Unexpected transaction type: {tx_type!r}")

    df = pd.DataFrame([{
        "description": description if description is not None else "",
        "amount": amount,
        "type": tx_type,
    }])

    X = feature_builder.transform(df)
    prediction = model.predict(X)

    return prediction[0]
