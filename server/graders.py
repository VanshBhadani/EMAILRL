from __future__ import annotations

from typing import List

from .models import EmailTriageAction, GradingResult
from .tasks import EmailSample


PRIORITY_WEIGHT = 0.4
CATEGORY_WEIGHT = 0.3
ACTION_WEIGHT = 0.3


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def grade_email_triage_action(
    action: EmailTriageAction,
    sample: EmailSample,
    prior_wrong_fields: List[str] | None = None,
) -> GradingResult:
    """
    Deterministic grader used by all tasks.

    Scoring weights:
      priority -> 0.4
      category -> 0.3
      action   -> 0.3

    Dangerous decisions are penalized, then score is clipped to [0, 1].
    """
    prior_wrong_fields = prior_wrong_fields or []

    priority_correct = action.priority == sample.expected.priority
    category_correct = action.category == sample.expected.category
    action_correct = action.action == sample.expected.action

    priority_component = PRIORITY_WEIGHT if priority_correct else 0.0
    category_component = CATEGORY_WEIGHT if category_correct else 0.0
    action_component = ACTION_WEIGHT if action_correct else 0.0

    base_score = priority_component + category_component + action_component

    wrong_fields: List[str] = []
    if not priority_correct:
        wrong_fields.append("priority")
    if not category_correct:
        wrong_fields.append("category")
    if not action_correct:
        wrong_fields.append("action")

    danger_reasons: List[str] = []
    dangerous_penalty = 0.0

    if sample.unsafe_if_ignored and action.action == "ignore":
        dangerous_penalty -= 0.5
        danger_reasons.append("ignored_urgent_or_sensitive_email")

    if sample.unsafe_if_reply and action.action == "reply":
        dangerous_penalty -= 0.4
        danger_reasons.append("replied_to_suspicious_email")

    if sample.unsafe_if_forward and action.action == "forward":
        dangerous_penalty -= 0.25
        danger_reasons.append("forwarded_potentially_malicious_email")

    if "phishing" in sample.risk_tags and action.category != "spam":
        dangerous_penalty -= 0.2
        danger_reasons.append("missed_phishing_classification")

    if "client-escalation" in sample.risk_tags and action.priority != "high":
        dangerous_penalty -= 0.15
        danger_reasons.append("underestimated_client_escalation")

    repeated_penalty = 0.0
    repeated_fields = sorted(set(wrong_fields).intersection(prior_wrong_fields))
    if repeated_fields:
        repeated_penalty -= 0.1 * float(len(repeated_fields))

    final_score = _clip01(base_score + dangerous_penalty + repeated_penalty)

    return GradingResult(
        score=final_score,
        priority_correct=priority_correct,
        category_correct=category_correct,
        action_correct=action_correct,
        priority_component=priority_component,
        category_component=category_component,
        action_component=action_component,
        dangerous_penalty=dangerous_penalty,
        repeated_penalty=repeated_penalty,
        wrong_fields=wrong_fields,
        danger_reasons=danger_reasons,
        notes={
            "base_score": base_score,
            "repeated_fields": repeated_fields,
            "risk_tags": sample.risk_tags,
        },
    )
