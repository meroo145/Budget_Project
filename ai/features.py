# ai/features.py
"""
Feature engineering for the Transaction Categorization model.

Fixes applied vs. the original version:
  1. Uses sklearn Pipeline + ColumnTransformer instead of a hand-rolled class
     -> guarantees fit/transform consistency, works with GridSearchCV/CV,
        and serializes as ONE object (no more model.pkl + features.pkl drift).
  2. Text is cleaned before TF-IDF (lowercased, strips reference numbers /
     currency symbols / extra whitespace) instead of raw TF-IDF on noisy text.
  3. TF-IDF now uses ngram_range=(1,2) and min_df=2 to cut noise from
     single-occurrence tokens and capture short phrases like "coffee shop".
  4. amount is log1p-transformed before scaling (money is heavy-tailed,
     StandardScaler alone lets outliers dominate).
  5. `type` uses OneHotEncoder(handle_unknown="ignore") instead of a
     hardcoded `== "income"` check, so unseen categories don't silently
     get mapped to "expense".
  6. Extra engineered features: description length (word count) and a
     "contains_digits" flag, both cheap but informative signals for
     transaction text (reference numbers, invoice numbers, etc).
  7. Missing/empty descriptions are explicitly handled (filled with "")
     instead of relying on implicit NaN behavior.

IMPORTANT: fit_transform must only ever be called on the TRAINING split.
See train.py — the train/test split now happens BEFORE feature fitting,
which fixes the data leakage present in the original pipeline (TF-IDF
vocabulary and the amount scaler were previously fit on the full dataset,
including the test set, which inflated the reported metrics).
"""

import re
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder, FunctionTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.base import BaseEstimator, TransformerMixin


# --------------------------------------------------------------------------
# Text cleaning
# --------------------------------------------------------------------------
_CLEAN_PATTERN = re.compile(r"[^a-zA-Z\u0600-\u06FF\s]")  # keep letters (EN+AR) + spaces
_MULTI_SPACE = re.compile(r"\s+")


def _clean_description(text: str) -> str:
    """Lowercase, strip digits/reference-numbers/currency symbols, collapse spaces."""
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return ""
    text = str(text).lower()
    text = _CLEAN_PATTERN.sub(" ", text)
    text = _MULTI_SPACE.sub(" ", text).strip()
    return text


class DescriptionCleaner(BaseEstimator, TransformerMixin):
    """Cleans the description column. Sklearn-compatible transformer."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        # X arrives as a 1-column DataFrame from ColumnTransformer
        series = X.iloc[:, 0] if isinstance(X, pd.DataFrame) else pd.Series(X)
        return series.apply(_clean_description)


class DescriptionStats(BaseEstimator, TransformerMixin):
    """Derives cheap-but-useful numeric signals from the raw description text."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        series = X.iloc[:, 0] if isinstance(X, pd.DataFrame) else pd.Series(X)
        series = series.fillna("").astype(str)

        word_count = series.apply(lambda s: len(s.split()))
        contains_digits = series.apply(lambda s: int(any(ch.isdigit() for ch in s)))

        return np.column_stack([word_count.values, contains_digits.values])


class LogTransform(BaseEstimator, TransformerMixin):
    """log1p transform, safe against negative/zero amounts."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = np.asarray(X, dtype=float)
        X = np.clip(X, a_min=0, a_max=None)  # guard against bad/negative input
        return np.log1p(X)


# --------------------------------------------------------------------------
# Public builder
# --------------------------------------------------------------------------
def build_feature_pipeline() -> ColumnTransformer:
    """
    Returns a ColumnTransformer expecting a DataFrame with columns:
    ['description', 'amount', 'type']
    """

    text_pipeline = Pipeline([
        ("clean", DescriptionCleaner()),
        ("tfidf", TfidfVectorizer(
            max_features=3000,      # reduced from 5000 — less overfitting risk on small datasets
            ngram_range=(1, 2),     # capture short phrases, not just single tokens
            min_df=2,               # drop tokens seen only once (noise)
            sublinear_tf=True,      # dampens the effect of very frequent tokens
        )),
    ])

    stats_pipeline = Pipeline([
        ("stats", DescriptionStats()),
        ("scale", StandardScaler()),
    ])

    amount_pipeline = Pipeline([
        ("log", LogTransform()),
        ("scale", StandardScaler()),
    ])

    type_pipeline = Pipeline([
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])

    preprocessor = ColumnTransformer(transformers=[
        ("text",   text_pipeline,   ["description"]),
        ("stats",  stats_pipeline,  ["description"]),
        ("amount", amount_pipeline, ["amount"]),
        ("type",   type_pipeline,   ["type"]),
    ])

    return preprocessor


class FeatureBuilder:
    """
    Thin backward-compatible wrapper around the ColumnTransformer pipeline,
    so train.py / predict.py can keep calling fit_transform() / transform()
    without needing to know about the internals.

    NOTE: fit_transform() must only be called on the training split.
    Calling it on the full dataset before train_test_split reintroduces
    the data leakage this refactor fixes.
    """

    def __init__(self):
        self.pipeline = build_feature_pipeline()
        self._is_fitted = False

    def fit_transform(self, df: pd.DataFrame):
        self._validate_columns(df)
        X = self.pipeline.fit_transform(df)
        self._is_fitted = True
        return X

    def transform(self, df: pd.DataFrame):
        if not self._is_fitted:
            raise RuntimeError(
                "FeatureBuilder.transform() called before fit_transform(). "
                "Load a fitted FeatureBuilder via joblib, or call fit_transform() first."
            )
        self._validate_columns(df)
        return self.pipeline.transform(df)

    @staticmethod
    def _validate_columns(df: pd.DataFrame):
        required = {"description", "amount", "type"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Input is missing required columns: {missing}")
