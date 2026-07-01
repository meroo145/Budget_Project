import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from ai.data_prep import load_transactions
from ai.features import FeatureBuilder


# 1. Load data
df = load_transactions()

# 2. Split X / y
X_raw = df.drop("label", axis=1)
y = df["label"]

# 3. Train/test split HAPPENS FIRST — before any fitting.
#    This is the fix for the data leakage in the original pipeline:
#    previously TF-IDF vocabulary + amount scaler were fit on the full
#    dataset (including what became the test set), which made the
#    evaluation metrics below overly optimistic.
X_train_raw, X_test_raw, y_train, y_test = train_test_split(
    X_raw, y,
    test_size=0.2,
    random_state=42,
    stratify=y,  # keeps category proportions consistent across train/test
)

# 4. Features — fit ONLY on train, transform test with the fitted state
feature_builder = FeatureBuilder()
X_train = feature_builder.fit_transform(X_train_raw)
X_test = feature_builder.transform(X_test_raw)

# 5. Model
model = LogisticRegression(
    max_iter=2000,
    class_weight="balanced",
)

# 6. Train
model.fit(X_train, y_train)

# 7. Evaluate — this report now reflects genuine held-out performance
y_pred = model.predict(X_test)

print(" Model Performance:\n")
print(classification_report(y_test, y_pred))

# 8. Save — single artifact bundling model + fitted feature pipeline,
#    so they can never drift out of sync with each other.
#    Saved inside ai/ (this file's own directory) so model_loader.py
#    (used by Django) finds it at <BASE_DIR>/ai/model_bundle.pkl
#    regardless of what directory train.py was run from.
import os
_save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_bundle.pkl")
joblib.dump(
    {"model": model, "feature_builder": feature_builder},
    _save_path,
)
print(f" Saved to: {_save_path}")

print(" Model trained + saved successfully!")
