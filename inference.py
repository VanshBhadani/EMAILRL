from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List

import requests
from openai import OpenAI

TASK_IDS = [
    "task_1_easy_spam_detection",
    "task_2_medium_work_prioritization",
    "task_3_hard_context_reasoning",
]

ALLOWED_PRIORITY = {"high", "medium", "low"}
ALLOWED_CATEGORY = {"work", "spam", "personal", "finance", "promotion"}
ALLOWED_ACTION = {"reply", "ignore", "forward", "escalate"}


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _safe_default_action() -> Dict[str, str]:
    return {"priority": "low", "category": "spam", "action": "ignore"}


def _normalize_action(candidate: Dict[str, Any]) -> Dict[str, str]:
    priority = str(candidate.get("priority", "")).strip().lower()
    category = str(candidate.get("category", "")).strip().lower()
    action = str(candidate.get("action", "")).strip().lower()

    if priority not in ALLOWED_PRIORITY:
        priority = "low"
    if category not in ALLOWED_CATEGORY:
        category = "spam"
    if action not in ALLOWED_ACTION:
        action = "ignore"

    return {"priority": priority, "category": category, "action": action}


def _extract_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    if not text:
        return {}

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}

    return {}


def decide_action(
    client: OpenAI,
    model_name: str,
    observation: Dict[str, Any],
) -> Dict[str, str]:
    payload = {
        "instruction": observation.get("instruction", ""),
        "subject": observation.get("subject", ""),
        "sender": observation.get("sender", ""),
        "email_body": observation.get("email_body", ""),
        "timestamp": observation.get("timestamp", ""),
        "thread_history": observation.get("thread_history", []),
        "attachments": observation.get("attachments", []),
        "last_feedback": observation.get("last_feedback", ""),
        "remaining_steps": observation.get("remaining_steps", 0),
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You are an email triage policy. Return JSON only with keys: "
                "priority, category, action. "
                "priority in [high, medium, low], "
                "category in [work, spam, personal, finance, promotion], "
                "action in [reply, ignore, forward, escalate]."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=True),
        },
    ]

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0,
    )

    content = response.choices[0].message.content or ""
    candidate = _extract_json_object(content)
    if not candidate:
        return _safe_default_action()

    return _normalize_action(candidate)


def run_episode(
    env_url: str,
    task_id: str,
    client: OpenAI,
    model_name: str,
    max_steps: int,
) -> None:
    print(f"[START] task={task_id} env={env_url} model={model_name}")

    rewards: List[float] = []
    step_idx = 0
    done = False
    success = False
    score = 0.0
    observation: Dict[str, Any] = {}
    terminal_error: str | None = None

    try:
        reset_response = requests.post(
            f"{env_url.rstrip('/')}/reset",
            json={"task_id": task_id},
            timeout=30,
        )
        reset_response.raise_for_status()
        reset_payload = reset_response.json()
        observation = dict(reset_payload.get("observation", {}))
    except Exception as exc:
        terminal_error = f"reset_failed:{type(exc).__name__}"
        print(
            "[STEP] step=0 action={} reward=0.00 done=true error="
            + terminal_error.replace(" ", "_")
        )
        print("[END] success=false steps=0 score=0.00 rewards=[]")
        return

    while not done and step_idx < max_steps:
        step_idx += 1

        action = _safe_default_action()
        error_text: str | None = None
        reward = 0.0

        try:
            action = decide_action(client=client, model_name=model_name, observation=observation)
            step_response = requests.post(
                f"{env_url.rstrip('/')}/step",
                json={"action": action},
                timeout=45,
            )
            step_response.raise_for_status()
            step_payload = step_response.json()

            reward = float(step_payload.get("reward") or 0.0)
            done = bool(step_payload.get("done", False))
            observation = dict(step_payload.get("observation", {}))
            rewards.append(reward)

            info = (observation.get("metadata") or {}).get("info") or {}
            if "grader_score" in info:
                score = _clip01(float(info.get("grader_score", 0.0)))
        except Exception as exc:
            done = True
            error_text = f"step_failed:{type(exc).__name__}"
            terminal_error = error_text
            rewards.append(reward)

        action_str = json.dumps(action, ensure_ascii=True, separators=(",", ":"))
        reward_str = f"{reward:.2f}"
        error_str = "null" if error_text is None else error_text.replace(" ", "_")

        print(
            f"[STEP] step={step_idx} action={action_str} reward={reward_str} "
            f"done={_bool_str(done)} error={error_str}"
        )

    if score <= 0.0:
        try:
            state_response = requests.get(f"{env_url.rstrip('/')}/state", timeout=20)
            if state_response.status_code == 200:
                state_payload = state_response.json()
                score = _clip01(float(state_payload.get("best_weighted_score", 0.0)))
        except Exception:
            pass

    if terminal_error is None and done:
        success = score >= 0.7

    rewards_str = "[" + ",".join(f"{r:.2f}" for r in rewards) + "]"
    print(
        f"[END] success={_bool_str(success)} steps={step_idx} "
        f"score={_clip01(score):.2f} rewards={rewards_str}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Baseline inference runner for email_triage_env")
    parser.add_argument("--task", default="", help="Single task_id to run")
    parser.add_argument("--max-steps", type=int, default=8, help="Maximum rollout steps")
    parser.add_argument(
        "--env-url",
        default=os.getenv("ENV_BASE_URL", "http://localhost:8000"),
        help="OpenEnv server base URL",
    )
    args = parser.parse_args()

    api_base_url = os.getenv("API_BASE_URL", "").strip()
    model_name = os.getenv("MODEL_NAME", "").strip()
    hf_token = os.getenv("HF_TOKEN", "").strip()

    if not api_base_url or not model_name or not hf_token:
        raise RuntimeError("Missing required env vars: API_BASE_URL, MODEL_NAME, HF_TOKEN")

    client = OpenAI(base_url=api_base_url, api_key=hf_token)

    tasks = [args.task] if args.task else TASK_IDS
    for task_id in tasks:
        run_episode(
            env_url=args.env_url,
            task_id=task_id,
            client=client,
            model_name=model_name,
            max_steps=max(1, args.max_steps),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
