# ai/advisor.py
"""
AI Advisor Service — Layer 3 of the AI Financial Advisor (Gemini integration)
plus the caching / orchestration that ties Layers 1–3 together.

RESPONSIBILITIES:
  1. Orchestrate: analyzer (numbers) -> insights (rules) -> Gemini (advice).
  2. Talk to Gemini, forcing STRICT JSON output (no free text ever reaches
     the DB or the template).
  3. Cache: results are written to the AIInsight model. Gemini is NEVER called
     on a normal page load — only when the cache is stale or the user clicks
     "Refresh". This keeps page loads fast and API usage low.
  4. Degrade gracefully: if google-generativeai isn't installed, no API key is
     configured, or Gemini errors/returns junk, we fall back to a deterministic
     rule-based advice payload so the page ALWAYS works locally.

PUBLIC ENTRY POINTS (used by the view layer — no logic lives in views):
  get_advice(user, force_refresh=False) -> AIInsight
  refresh_advice(user)                  -> AIInsight
"""

import json
import logging

from django.conf import settings
from django.utils import timezone

from Budget.models import AIInsight
from ai.analyzer import analyze_user_finances
from ai.insights import generate_insights

logger = logging.getLogger(__name__)

# How long a cached AIInsight is considered "fresh". Within this window,
# get_advice() returns the stored row and does NOT call Gemini.
CACHE_TTL_HOURS = 24

_VALID_PRIORITIES = {'low', 'medium', 'high'}


# =============================================================================
#  PUBLIC ENTRY POINTS
# =============================================================================

def get_advice(user, force_refresh: bool = False) -> AIInsight:
    """
    Return the user's current AI advice.

    Fast path: if a fresh (< CACHE_TTL_HOURS old) AIInsight exists and we
    aren't force-refreshing, return it WITHOUT calling Gemini. Otherwise
    generate a new one.
    """
    latest = AIInsight.objects.filter(user=user).order_by('-created').first()

    if latest and not force_refresh and _is_fresh(latest):
        return latest

    return refresh_advice(user)


def refresh_advice(user) -> AIInsight:
    """
    Force a full regeneration: analyze -> insights -> advice, then persist.
    Called by the manual "Refresh" button (and by any periodic job).
    """
    analysis = analyze_user_finances(user)
    insights = generate_insights(analysis)
    advice   = _build_advice(analysis, insights)

    return AIInsight.objects.create(
        user=user,
        title=advice['title'],
        advice=advice['advice'],
        priority=advice['priority'],
        reason=advice['reason'],
        source=advice['source'],
        context={'analysis': analysis, 'insights': insights},
    )


# =============================================================================
#  ADVICE GENERATION  (Gemini first, deterministic fallback second)
# =============================================================================

def _build_advice(analysis: dict, insights: list) -> dict:
    """
    Try Gemini; on ANY failure fall back to rule-based advice so the feature
    never breaks locally. Always returns a dict with keys:
    title, advice, priority, reason, source.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        logger.info("GEMINI_API_KEY not set — using rule-based fallback advice.")
        return _fallback_advice(analysis, insights)

    try:
        return _call_gemini(analysis, insights, api_key)
    except Exception as e:  # noqa: BLE001 — never let advice generation 500 the page
        logger.warning("Gemini advice failed (%s) — falling back to rules.", e)
        return _fallback_advice(analysis, insights)


def _call_gemini(analysis: dict, insights: list, api_key: str) -> dict:
    """
    Send the structured context to Gemini and force STRICT JSON back.

    Raises on any problem (missing package, bad response, invalid JSON) so the
    caller can fall back. The model is instructed — and constrained via
    response_mime_type — to return ONLY the advice JSON object.
    """
    import google.generativeai as genai  # imported lazily so the app runs without it

    genai.configure(api_key=api_key)
    model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash')

    model = genai.GenerativeModel(
        model_name,
        generation_config={
            'response_mime_type': 'application/json',
            'temperature': 0.4,
        },
    )

    response = model.generate_content(_build_prompt(analysis, insights))
    payload = _parse_json(response.text)

    return _normalize_advice(payload, source='gemini')


def _build_prompt(analysis: dict, insights: list) -> str:
    """
    The Gemini prompt. It receives ONLY the pre-computed JSON — never raw rows
    — and is told exactly what JSON shape to return.
    """
    return f"""You are a concise, practical personal-finance advisor.

Below is a user's financial summary and a list of rule-based observations,
both as JSON. Base your advice ONLY on this data. Do not invent numbers.

FINANCIAL_SUMMARY:
{json.dumps(analysis, indent=2)}

RULE_BASED_INSIGHTS:
{json.dumps(insights, indent=2)}

Return ONE actionable piece of advice as a STRICT JSON object with EXACTLY
these keys and nothing else:

{{
  "title":    "short headline (max 8 words)",
  "advice":   "2-3 sentences of specific, actionable advice",
  "priority": "low | medium | high",
  "reason":   "one sentence explaining which number drove this advice"
}}

Rules:
- Output ONLY the JSON object. No markdown, no commentary, no code fences.
- "priority" MUST be exactly one of: low, medium, high.
- Be specific: reference the actual categories and amounts from the data."""


def _fallback_advice(analysis: dict, insights: list) -> dict:
    """
    Deterministic advice built straight from the insights when Gemini is
    unavailable. Priority maps from the most severe insight present.
    """
    if analysis['transaction_count'] == 0:
        return {
            'title':    'Add your first transactions',
            'advice':   'Start logging expenses so the advisor can analyse your '
                        'spending and give tailored guidance.',
            'priority': 'low',
            'reason':   'No transactions recorded yet.',
            'source':   'fallback',
        }

    severity_to_priority = {'critical': 'high', 'warning': 'medium',
                            'info': 'low', 'success': 'low'}
    top = insights[0] if insights else None

    if top:
        return {
            'title':    _headline_for(top),
            'advice':   top['message'] + ' ' + _suggestion_for(top['code']),
            'priority': severity_to_priority.get(top['severity'], 'medium'),
            'reason':   top['message'],
            'source':   'fallback',
        }

    return {
        'title':    'Your finances look steady',
        'advice':   'No red flags detected. Keep tracking your spending to stay '
                    'on top of your budget.',
        'priority': 'low',
        'reason':   'No threshold-based warnings were triggered.',
        'source':   'fallback',
    }


# =============================================================================
#  HELPERS
# =============================================================================

def _is_fresh(insight: AIInsight) -> bool:
    age = timezone.now() - insight.created
    return age.total_seconds() < CACHE_TTL_HOURS * 3600


def _parse_json(text: str) -> dict:
    """Parse Gemini output, tolerating stray ```json code fences."""
    cleaned = text.strip()
    if cleaned.startswith('```'):
        cleaned = cleaned.strip('`')
        if cleaned.lower().startswith('json'):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())


def _normalize_advice(payload: dict, source: str) -> dict:
    """
    Validate + coerce a raw advice dict into our exact contract. Raises
    ValueError if required text is missing so the caller can fall back.
    """
    title  = str(payload.get('title', '')).strip()
    advice = str(payload.get('advice', '')).strip()
    reason = str(payload.get('reason', '')).strip()
    priority = str(payload.get('priority', 'medium')).strip().lower()

    if not title or not advice:
        raise ValueError("Gemini response missing 'title' or 'advice'.")
    if priority not in _VALID_PRIORITIES:
        priority = 'medium'

    return {
        'title':    title[:200],
        'advice':   advice,
        'priority': priority,
        'reason':   reason,
        'source':   source,
    }


def _headline_for(insight: dict) -> str:
    return {
        'category_dominance': 'Rebalance your spending',
        'high_food_spending': 'Food spending is high',
        'budget_exceeded':    'You went over budget',
        'budget_near_limit':  'Budget almost used up',
        'negative_cashflow':  'You are overspending',
        'low_savings':        'Boost your savings rate',
        'healthy_savings':    'Great savings habit',
        'spending_up':        'Spending is climbing',
        'spending_down':      'Spending is trending down',
    }.get(insight['code'], 'Financial insight')


def _suggestion_for(code: str) -> str:
    return {
        'category_dominance': 'Try setting a category budget to keep it in check.',
        'high_food_spending': 'Consider meal planning or a weekly food cap.',
        'budget_exceeded':    'Pause non-essential spending in this category.',
        'budget_near_limit':  'Slow down here for the rest of the month.',
        'negative_cashflow':  'Cut discretionary categories until you break even.',
        'low_savings':        'Automate a fixed transfer to savings each payday.',
        'healthy_savings':    'Keep it up and consider investing the surplus.',
        'spending_up':        'Review what changed since last month.',
        'spending_down':      'Lock in the habit that caused the drop.',
    }.get(code, 'Keep tracking your spending to stay on target.')
