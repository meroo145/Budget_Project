import os
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.semi_supervised import SelfTrainingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from ai.data_prep import load_transactions, load_unlabeled_transactions
from ai.features import FeatureBuilder


DEFAULT_CONFIDENCE_THRESHOLD = 0.75
DEFAULT_MAX_ITERATIONS = 10


def train_model(confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
                 max_iterations: int = DEFAULT_MAX_ITERATIONS,
                 verbose: bool = True) -> dict:
    """
    Trains the semi-supervised transaction-category model and saves it to
    ai/model_bundle.pkl.

    Wrapped in a function (rather than top-level script code) so it can be
    called both:
      - standalone: `python -m ai.train`
      - from Django: `python manage.py retrain_category_model`
        (see Budget/management/commands/retrain_category_model.py)

    Returns a small summary dict so callers (like the management command)
    can print/log results without re-parsing stdout.
    """

    # 1. Load LABELED data (ground truth) and UNLABELED data (candidates for pseudo-labeling)
    labeled_df = load_transactions()
    unlabeled_df = load_unlabeled_transactions()

    if verbose:
        print(f"Labeled transactions:   {len(labeled_df)}")
        print(f"Unlabeled transactions: {len(unlabeled_df)}")

    if len(labeled_df) < 20:
        raise ValueError(
            "Not enough labeled data to train reliably (need at least ~20 rows). "
            "Add more categorized transactions first."
        )

    X_labeled_raw = labeled_df.drop("label", axis=1)
    y_labeled = labeled_df["label"]

    # --------------------------------------------------------------------
    # 2. Split the LABELED data into train/test FIRST.
    #    The test set stays 100% clean ground truth -- never mixed with
    #    unlabeled data, never touched by pseudo-labeling.
    # --------------------------------------------------------------------
    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X_labeled_raw, y_labeled,
        test_size=0.2,
        random_state=42,
        stratify=y_labeled,
    )

    # --------------------------------------------------------------------
    # 3. Combine labeled-train + unlabeled rows for feature fitting and
    #    self-training. Unlabeled rows get sklearn's sentinel label -1.
    # --------------------------------------------------------------------
    if len(unlabeled_df) > 0:
        X_combined_raw = pd.concat(
            [X_train_raw.reset_index(drop=True), unlabeled_df.reset_index(drop=True)],
            ignore_index=True,
        )
        y_combined = pd.concat(
            [y_train.reset_index(drop=True), pd.Series([-1] * len(unlabeled_df))],
            ignore_index=True,
        )
    else:
        if verbose:
            print("No unlabeled transactions found -- training normally (fully supervised).")
        X_combined_raw = X_train_raw.reset_index(drop=True)
        y_combined = y_train.reset_index(drop=True)

    feature_builder = FeatureBuilder()
    X_combined = feature_builder.fit_transform(X_combined_raw)
    X_test = feature_builder.transform(X_test_raw)

    # --------------------------------------------------------------------
    # 4. Self-training wrapper around LogisticRegression.
    # --------------------------------------------------------------------
    base_model = LogisticRegression(max_iter=2000, class_weight="balanced")

    model = SelfTrainingClassifier(
        base_model,
        threshold=confidence_threshold,
        criterion="threshold",
        max_iter=max_iterations,
        verbose=verbose,
    )

    model.fit(X_combined, y_combined)

    # --------------------------------------------------------------------
    # 5. Evaluate ONLY on the clean, fully-labeled held-out test set.
    # --------------------------------------------------------------------
    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True)
    report_text = classification_report(y_test, y_pred)

    if verbose:
        print("\n Model Performance (held-out labeled test set only):\n")
        print(report_text)

    # --------------------------------------------------------------------
    # 6. Report how many unlabeled rows got confidently pseudo-labeled.
    # --------------------------------------------------------------------
    n_pseudo_labeled = 0
    if len(unlabeled_df) > 0:
        transduced_unlabeled = model.transduction_[len(X_train_raw):]
        n_pseudo_labeled = int((transduced_unlabeled != -1).sum())
        if verbose:
            print(
                f"\nPseudo-labeled {n_pseudo_labeled} / {len(unlabeled_df)} "
                f"unlabeled transactions (threshold={confidence_threshold})."
            )
            print(
                "Recommendation: manually spot-check a random sample of these "
                "before fully trusting them."
            )

    # --------------------------------------------------------------------
    # 7. Save -- single artifact bundling model + fitted feature pipeline.
    # --------------------------------------------------------------------
    save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_bundle.pkl")
    joblib.dump({"model": model, "feature_builder": feature_builder}, save_path)

    if verbose:
        print(f"\n Saved to: {save_path}")
        print(" Model trained + saved successfully!")

    return {
        "labeled_count": len(labeled_df),
        "unlabeled_count": len(unlabeled_df),
        "pseudo_labeled_count": n_pseudo_labeled,
        "test_accuracy": report["accuracy"],
        "save_path": save_path,
    }


if __name__ == "__main__":
    train_model()