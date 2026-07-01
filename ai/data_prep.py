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
    Load transactions from Django DB and convert to pandas DataFrame
    """

    qs = Transaction.objects.all().values(
        "description",
        "amount",
        "type",
        "category__name",
    )

    df = pd.DataFrame(qs)

    # remove empty rows
    df.dropna(inplace=True)

    # rename label column
    df.rename(columns={"category__name": "label"}, inplace=True)

    return df
