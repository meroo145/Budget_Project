# ai/predict.py

import joblib
import pandas as pd


# Load the single bundled artifact (model + fitted feature pipeline)
_bundle = joblib.load("model_bundle.pkl")
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
