# ai/insights.py
"""
Insight Generator — Layer 2 of the AI Financial Advisor.

RULE-BASED ONLY. No AI, no network. This layer turns the raw numbers from
ai/analyzer.py into a structured list of human-meaningful observations using
simple, auditable thresholds. Every insight is a dict (never free text) so
the downstream Gemini layer receives clean, typed signals it can reason over
— and so the UI can style each one by severity.

WHY RULES AND NOT AI HERE:
  These checks ("food is over 40% of spend", "budget is 80% used") must be
  deterministic, explainable, and free. AI is reserved for Layer 3, where it
  turns these facts into personalised natural-language advice.

PUBLIC ENTRY POINT:
  generate_insights(analysis: dict) -> list[dict]

Each insight has the shape:
  {"code": str, "severity": "success|info|warning|critical", "message": str}
"""


# =============================================================================
#  TUNABLE THRESHOLDS  (change here, nowhere else)
# =============================================================================
CATEGORY_DOMINANCE_PCT = 40   # a single category above this share is a red flag
FOOD_WARNING_PCT       = 40   # food specifically tends to creep up unnoticed
BUDGET_ALERT_PCT       = 80   # nearing a budget limit
LOW_SAVINGS_PCT        = 10   # keeping less than this share of income is risky
HEALTHY_SAVINGS_PCT    = 20   # keeping this much or more is worth celebrating


# =============================================================================
#  PUBLIC ENTRY POINT
# =============================================================================

def generate_insights(analysis: dict) -> list:
    """
    Apply every rule to the analyzer output and return an ordered list of
    insight dicts (most severe first). Returns a single 'no data' insight
    when the user has no transactions yet.
    """
    if analysis['transaction_count'] == 0:
        return [_insight('no_data', 'info',
                         'No transactions yet — add some expenses to unlock insights.')]

    insights = []
    insights += _category_rules(analysis)
    insights += _budget_rules(analysis)
    insights += _cashflow_rules(analysis)
    insights += _trend_rules(analysis)

    # Most severe first so the UI (and Gemini) see the important stuff up top.
    order = {'critical': 0, 'warning': 1, 'info': 2, 'success': 3}
    insights.sort(key=lambda i: order[i['severity']])
    return insights


# =============================================================================
#  RULE GROUPS
# =============================================================================

def _category_rules(analysis: dict) -> list:
    """Category-share rules: dominance, and the specific food watch."""
    out = []
    highest = analysis['highest_category']
    if not highest:
        return out

    if highest['percentage'] >= CATEGORY_DOMINANCE_PCT:
        out.append(_insight(
            'category_dominance', 'warning',
            f"{highest['category']} is {highest['percentage']}% of your spending "
            f"(${highest['amount']}) — one category is dominating your budget."
        ))

    for cat in analysis['spending_by_category']:
        if cat['category'] == 'Food' and cat['percentage'] >= FOOD_WARNING_PCT:
            out.append(_insight(
                'high_food_spending', 'warning',
                f"Food spending is high at {cat['percentage']}% (${cat['amount']}) "
                f"of your total expenses."
            ))
    return out


def _budget_rules(analysis: dict) -> list:
    """Per-budget usage rules: over-limit (critical) and nearing-limit (warning)."""
    out = []
    for b in analysis['budget_usage']:
        if b['over_limit']:
            out.append(_insight(
                'budget_exceeded', 'critical',
                f"Over budget on {b['category']}: spent ${b['spent']} of ${b['budget']} "
                f"({b['percentage']}%)."
            ))
        elif b['percentage'] >= BUDGET_ALERT_PCT:
            out.append(_insight(
                'budget_near_limit', 'warning',
                f"{b['category']} budget is {b['percentage']}% used "
                f"(${b['spent']} of ${b['budget']})."
            ))
    return out


def _cashflow_rules(analysis: dict) -> list:
    """Income-vs-expense and savings-rate health."""
    out = []
    if analysis['total_expenses'] > analysis['total_income']:
        out.append(_insight(
            'negative_cashflow', 'critical',
            f"You're spending more than you earn "
            f"(${analysis['total_expenses']} out vs ${analysis['total_income']} in)."
        ))

    rate = analysis['savings_rate']
    if analysis['total_income'] > 0:
        if rate < LOW_SAVINGS_PCT:
            out.append(_insight(
                'low_savings', 'warning',
                f"Your savings rate is only {rate}% of income — aim for 20%+."
            ))
        elif rate >= HEALTHY_SAVINGS_PCT:
            out.append(_insight(
                'healthy_savings', 'success',
                f"Great job — you're saving {rate}% of your income."
            ))
    return out


def _trend_rules(analysis: dict) -> list:
    """Month-over-month spending trend."""
    out = []
    change = analysis['monthly_comparison']['change_percent']
    if change is None:
        return out

    if change >= 25:
        out.append(_insight(
            'spending_up', 'warning',
            f"Spending is up {change}% versus last month."
        ))
    elif change <= -15:
        out.append(_insight(
            'spending_down', 'success',
            f"Spending is down {abs(change)}% versus last month — nice."
        ))
    return out


# =============================================================================
#  HELPER
# =============================================================================

def _insight(code: str, severity: str, message: str) -> dict:
    return {'code': code, 'severity': severity, 'message': message}
