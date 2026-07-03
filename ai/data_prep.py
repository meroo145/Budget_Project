import os
import django
import pandas as pd

# 1. setup Django FIRST
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Project.settings")
django.setup()

# 2. import models AFTER setup
from Budget.models import Transaction


def load_transactions():
    """
    Load LABELED transactions (those with a category) from the Django DB as a
    pandas DataFrame with columns: description, amount, type, label.

    These are the ground-truth rows the model trains on. Rows with no category
    are dropped here and instead surfaced by load_unlabeled_transactions().
    """

    qs = Transaction.objects.filter(category__isnull=False).values(
        "description",
        "amount",
        "type",
        "category__name",
    )

    # Explicit columns so an empty queryset still yields the right shape
    # (bare pd.DataFrame([]) has no columns and breaks the rename/drop below).
    df = pd.DataFrame(
        list(qs),
        columns=["description", "amount", "type", "category__name"],
    )

    # rename label column
    df.rename(columns={"category__name": "label"}, inplace=True)

    return df


def load_unlabeled_transactions():
    """
    Load UNLABELED transactions (category is NULL) from the Django DB as a
    pandas DataFrame with columns: description, amount, type.

    These are the genuine "Not sure -- let AI categorize it later" rows the
    user skipped (category_id=None; see Budget/views.py). The semi-supervised
    trainer (ai/train.py) feeds them in with sklearn's -1 sentinel label so
    self-training can pseudo-label them.

    NOTE: no `label` column is returned -- these rows have no ground truth.
    The explicit `columns=` keeps the shape correct even when there are zero
    unlabeled rows, so feature building never crashes on a missing column.
    """
    qs = Transaction.objects.filter(category__isnull=True).values(
        "description",
        "amount",
        "type",
    )

    return pd.DataFrame(
        list(qs),
        columns=["description", "amount", "type"],
    )
