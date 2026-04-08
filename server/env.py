from __future__ import annotations

from typing import Any, Dict, Tuple
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import EnvironmentMetadata

from .graders import grade_email_triage_action
from .models import (
    EmailTriageAction,
    EmailTriageObservation,
    EmailTriageState,
    RewardBreakdown,
)
from .tasks import (
    EmailSample,
    TaskDefinition,
    choose_sample_index,
    choose_task_id,
    get_task,
)


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class EmailTriageEnvCore:
    """
    Core deterministic environment implementing gym-style APIs.

    - step(action) -> (observation, reward, done, info)
    - reset() -> observation
    - state() -> state snapshot
    """

    def __init__(self) -> None:
        self._reset_counter = 0
        self._current_task: TaskDefinition | None = None
        self._current_sample: EmailSample | None = None
        self._state = EmailTriageState(
            episode_id=str(uuid4()),
            step_count=0,
            max_steps=6,
            task_id="",
            task_name="",
            current_email_id="",
        )

    def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        **kwargs: Any,
    ) -> EmailTriageObservation:
        task_id = choose_task_id(kwargs.get("task_id"), self._reset_counter)
        task = get_task(task_id)

        sample_index = choose_sample_index(
            sample_count=len(task.samples),
            reset_counter=self._reset_counter,
            seed=seed,
            sample_index=kwargs.get("sample_index"),
        )
        sample = task.samples[sample_index]

        max_steps = int(kwargs.get("max_steps", task.max_steps))
        max_steps = int(_clip(float(max_steps), 5.0, 10.0))

        self._current_task = task
        self._current_sample = sample
        self._state = EmailTriageState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_id=task.task_id,
            task_name=task.task_name,
            current_email_id=sample.email_id,
            sample_index=sample_index,
            max_steps=max_steps,
            cumulative_reward=0.0,
            best_weighted_score=0.0,
            last_weighted_score=0.0,
            recent_wrong_fields=[],
            dangerous_events=0,
        )

        self._reset_counter += 1

        return self._build_observation(
            reward=0.0,
            done=False,
            last_feedback="Environment reset. Analyze the email and submit triage fields.",
            info={
                "task_id": task.task_id,
                "sample_index": sample_index,
                "deterministic": True,
            },
        )

    def state(self) -> EmailTriageState:
        return self._state

    def step(
        self,
        action: EmailTriageAction,
    ) -> Tuple[EmailTriageObservation, float, bool, Dict[str, Any]]:
        if self._current_task is None or self._current_sample is None:
            self.reset()

        assert self._current_task is not None
        assert self._current_sample is not None

        self._state.step_count += 1

        grading = grade_email_triage_action(
            action=action,
            sample=self._current_sample,
            prior_wrong_fields=self._state.recent_wrong_fields,
        )

        progress_bonus = max(0.0, grading.score - self._state.best_weighted_score) * 0.2
        drift_penalty = -0.05 if grading.score < self._state.last_weighted_score else 0.0
        terminal_bonus = 0.0

        solved = grading.priority_correct and grading.category_correct and grading.action_correct
        done = solved or self._state.step_count >= self._state.max_steps

        if solved:
            terminal_bonus += 0.2
        elif done:
            terminal_bonus -= 0.2

        reward = (
            grading.score
            + progress_bonus
            + grading.dangerous_penalty
            + grading.repeated_penalty
            + drift_penalty
            + terminal_bonus
        )
        reward = round(_clip(reward, -1.0, 1.0), 4)

        self._state.cumulative_reward += reward
        self._state.best_weighted_score = max(self._state.best_weighted_score, grading.score)
        self._state.last_weighted_score = grading.score
        self._state.recent_wrong_fields = grading.wrong_fields
        self._state.dangerous_events += len(grading.danger_reasons)

        breakdown = RewardBreakdown(
            priority_component=grading.priority_component,
            category_component=grading.category_component,
            action_component=grading.action_component,
            weighted_score=grading.score,
            progress_bonus=progress_bonus,
            dangerous_penalty=grading.dangerous_penalty,
            repeated_penalty=grading.repeated_penalty,
            drift_penalty=drift_penalty,
            terminal_bonus=terminal_bonus,
            total_reward=reward,
        )

        info: Dict[str, Any] = {
            "grader_score": grading.score,
            "priority_correct": grading.priority_correct,
            "category_correct": grading.category_correct,
            "action_correct": grading.action_correct,
            "wrong_fields": grading.wrong_fields,
            "danger_reasons": grading.danger_reasons,
            "reward_breakdown": breakdown.model_dump(),
            "step_count": self._state.step_count,
            "max_steps": self._state.max_steps,
        }

        observation = self._build_observation(
            reward=reward,
            done=done,
            last_feedback=self._compose_feedback(grading.wrong_fields, grading.danger_reasons, solved),
            info=info,
        )

        return observation, reward, done, info

    def _build_observation(
        self,
        reward: float,
        done: bool,
        last_feedback: str,
        info: Dict[str, Any],
    ) -> EmailTriageObservation:
        if self._current_task is None or self._current_sample is None:
            raise RuntimeError("Environment has no active sample. Call reset() first.")

        remaining_steps = max(0, self._state.max_steps - self._state.step_count)

        metadata = {
            "info": info,
            "metrics": {
                "cumulative_reward": round(self._state.cumulative_reward, 4),
                "best_weighted_score": round(self._state.best_weighted_score, 4),
                "dangerous_events": self._state.dangerous_events,
            },
        }

        return EmailTriageObservation(
            email_id=self._current_sample.email_id,
            subject=self._current_sample.subject,
            sender=self._current_sample.sender,
            email_body=self._current_sample.email_body,
            timestamp=self._current_sample.timestamp,
            thread_history=self._current_sample.thread_history,
            attachments=self._current_sample.attachments,
            task_id=self._current_task.task_id,
            task_name=self._current_task.task_name,
            instruction=self._current_task.instruction,
            remaining_steps=remaining_steps,
            last_feedback=last_feedback,
            reward=reward,
            done=done,
            metadata=metadata,
        )

    @staticmethod
    def _compose_feedback(
        wrong_fields: list[str],
        danger_reasons: list[str],
        solved: bool,
    ) -> str:
        if solved:
            return "Correct triage. Episode solved."

        parts: list[str] = []
        if wrong_fields:
            parts.append("Incorrect fields: " + ", ".join(wrong_fields))
        if danger_reasons:
            parts.append("Safety issue: " + "; ".join(danger_reasons))
        if not parts:
            parts.append("Partially correct. Refine your decision.")
        return " | ".join(parts)


class EmailTriageEnvironment(Environment):
    """OpenEnv adapter wrapping EmailTriageEnvCore."""

    SUPPORTS_CONCURRENT_SESSIONS: bool = False

    def __init__(self) -> None:
        super().__init__()
        self._core = EmailTriageEnvCore()

    def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        **kwargs: Any,
    ) -> EmailTriageObservation:
        return self._core.reset(seed=seed, episode_id=episode_id, **kwargs)

    def step(
        self,
        action: EmailTriageAction,
        timeout_s: float | None = None,
        **kwargs: Any,
    ) -> EmailTriageObservation:
        observation, _, _, _ = self._core.step(action)
        return observation

    @property
    def state(self) -> EmailTriageState:
        return self._core.state()

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="email_triage_env",
            description=(
                "Realistic email triage environment with deterministic multi-task grading, "
                "safety penalties, and shaped rewards."
            ),
            version="1.0.0",
        )
