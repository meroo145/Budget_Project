# ai/analyzer.py
"""
Financial Analyzer — Layer 1 of the AI Financial Advisor.

NO AI / NO NETWORK CALLS HAPPEN HERE. This module is pure, deterministic
number-crunching over the user's own Transaction / Budget rows. It exists
so that the (expensive, non-deterministic) Gemini layer is only ever handed
a clean, structured, already-computed JSON context — never raw DB rows and
never the job of doing arithmetic it might get wrong.

WHY A SEPARATE MODULE:
  Separation of concerns. The advisor service (ai/advisor.py) orchestrates,
  the insight layer (ai/insights.py) applies human rules, and THIS layer is
  the single source of truth for "what do the numbers actually say". Any of
  the three can be tested in isolation.

PUBLIC ENTRY POINT:
  analyze_user_finances(user) -> dict   (JSON-serializable)

NOTE ON FIELDS:
  The Transaction model stores the free-text label as `description` (there is
  no `merchant` column), so merchant-style analysis is derived from category,
  which is the reliable structured signal.
"""

from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from Budget.models import Transaction, Budget


# =============================================================================
#  PUBLIC ENTRY POINT
# =============================================================================

def analyze_user_finances(user) -> dict:
    """
    Build the full structured financial context for a single user.

    Returns a JSON-serializable dict — this is the ONLY thing that ever gets
    passed downstream to the insight generator and the Gemini prompt.
    """
    expenses = Transaction.objects.filter(user=user, type='expense')
    income   = Transaction.objects.filter(user=user, type='income')

    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0.0
    total_income   = income.aggregate(Sum('amount'))['amount__sum'] or 0.0

    spending_by_category = _spending_by_category(expenses, total_expenses)

    return {
        'total_income':         round(total_income, 2),
        'total_expenses':       round(total_expenses, 2),
        'balance':              round(total_income - total_expenses, 2),
        'savings_rate':         _savings_rate(total_income, total_expenses),
        'transaction_count':    expenses.count() + income.count(),
        'spending_by_category': spending_by_category,
        'highest_category':     spending_by_category[0] if spending_by_category else None,
        'monthly_comparison':   _monthly_comparison(expenses),
        'budget_usage':         _budget_usage(user, expenses),
        'generated_at':         timezone.now().isoformat(),
    }


# =============================================================================
#  INTERNAL HELPERS  (each does exactly one thing)
# =============================================================================

def _spending_by_category(expenses, total_expenses) -> list:
    """
    Total + percentage spent per category, sorted highest first.
    Uncategorized transactions are bucketed under 'Uncategorized'.
    """
    rows = (
        expenses.values('category__name')
                .annotate(amount=Sum('amount'))
                .order_by('-amount')
    )

    result = []
    for row in rows:
        amount = row['amount'] or 0.0
        result.append({
            'category':   row['category__name'] or 'Uncategorized',
            'amount':     round(amount, 2),
            'percentage': _percent(amount, total_expenses),
        })
    return result


def _monthly_comparison(expenses) -> dict:
    """
    Compare this calendar month's expenses against last month's, so the
    advisor can say "you're spending more/less than last month".
    """
    today          = timezone.now().date()
    first_of_month = today.replace(day=1)
    last_month_end = first_of_month - timedelta(days=1)
    first_of_prev  = last_month_end.replace(day=1)

    this_month = expenses.filter(date__gte=first_of_month) \
                         .aggregate(Sum('amount'))['amount__sum'] or 0.0
    prev_month = expenses.filter(date__gte=first_of_prev, date__lt=first_of_month) \
                         .aggregate(Sum('amount'))['amount__sum'] or 0.0

    return {
        'current_month':  round(this_month, 2),
        'previous_month': round(prev_month, 2),
        'change_percent': _percent(this_month - prev_month, prev_month) if prev_month else None,
    }


def _budget_usage(user, expenses) -> list:
    """
    For every budget the user has set, how much of it is already spent.
    Mirrors the logic in Budget/views.py:budgets_page so numbers match the
    Budgets screen exactly.
    """
    usage = []
    for budget in Budget.objects.filter(user=user).select_related('category'):
        if budget.amount <= 0:
            continue  # skip zero-amount budgets (avoids divide-by-zero)

        spent = expenses.filter(category=budget.category) \
                        .aggregate(Sum('amount'))['amount__sum'] or 0.0
        percentage = _percent(spent, budget.amount)

        usage.append({
            'category':   budget.category.name if budget.category else 'Uncategorized',
            'budget':     round(budget.amount, 2),
            'spent':      round(spent, 2),
            'percentage': percentage,
            'over_limit': spent > budget.amount,
        })
    return usage


# --- tiny math utilities -----------------------------------------------------

def _percent(part, whole) -> float:
    """Safe percentage: returns 0.0 instead of blowing up on a zero divisor."""
    if not whole:
        return 0.0
    return round((part / whole) * 100, 1)


def _savings_rate(total_income, total_expenses) -> float:
    """Percentage of income kept (not spent). 0.0 when there is no income."""
    if not total_income:
        return 0.0
    return round(((total_income - total_expenses) / total_income) * 100, 1)
