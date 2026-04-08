from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field

from openenv.core.env_server.types import Action, Observation, State


PriorityLabel = Literal["high", "medium", "low"]
CategoryLabel = Literal["work", "spam", "personal", "finance", "promotion"]
ActionLabel = Literal["reply", "ignore", "forward", "escalate"]


class ThreadMessage(BaseModel):
    sender: str = Field(..., description="Sender from an earlier message in the thread")
    subject: str = Field(..., description="Subject line from the earlier message")
    body: str = Field(..., description="Body text from the earlier message")
    timestamp: str = Field(..., description="ISO-like timestamp string")


class AttachmentMetadata(BaseModel):
    file_name: str = Field(..., description="Attachment file name")
    mime_type: str = Field(..., description="Attachment media type")
    size_kb: int = Field(..., ge=0, description="Attachment size in KB")


class EmailTriageAction(Action):
    """Action output expected from the policy."""

    priority: PriorityLabel = Field(..., description="Predicted priority")
    category: CategoryLabel = Field(..., description="Predicted category")
    action: ActionLabel = Field(..., description="Recommended next action")
    rationale: str | None = Field(
        default=None,
        description="Optional concise explanation for auditing",
    )


class EmailTriageObservation(Observation):
    """Observation shown to the agent for each email triage decision."""

    email_id: str = Field(..., description="Unique email identifier")
    subject: str = Field(..., description="Email subject line")
    sender: str = Field(..., description="Sender address or display name")
    email_body: str = Field(..., description="Main body text")
    timestamp: str = Field(..., description="ISO-like timestamp string")
    thread_history: List[ThreadMessage] = Field(
        default_factory=list,
        description="Previous messages in the same thread",
    )
    attachments: List[AttachmentMetadata] = Field(
        default_factory=list,
        description="Attachment metadata only, no file payload",
    )
    task_id: str = Field(..., description="Task identifier")
    task_name: str = Field(..., description="Human-readable task name")
    instruction: str = Field(..., description="Task instruction for the policy")
    remaining_steps: int = Field(
        default=0,
        ge=0,
        description="How many steps are left in the episode",
    )
    last_feedback: str = Field(
        default="",
        description="Environment feedback from the most recent action",
    )


class EmailTriageState(State):
    """Server-side state for episode tracking and diagnostics."""

    task_id: str = Field(default="", description="Current task identifier")
    task_name: str = Field(default="", description="Current task name")
    current_email_id: str = Field(default="", description="Current email id")
    sample_index: int = Field(default=0, ge=0, description="Index of selected sample")
    max_steps: int = Field(default=6, ge=1, description="Episode step limit")
    cumulative_reward: float = Field(default=0.0, description="Reward sum in episode")
    best_weighted_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Best correctness score reached so far",
    )
    last_weighted_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Correctness score from the latest step",
    )
    recent_wrong_fields: List[str] = Field(
        default_factory=list,
        description="Fields that were wrong in the previous step",
    )
    dangerous_events: int = Field(
        default=0,
        ge=0,
        description="Count of dangerous decisions in this episode",
    )


class RewardBreakdown(BaseModel):
    """Detailed reward-shaping components for debugging and evaluation."""

    priority_component: float = 0.0
    category_component: float = 0.0
    action_component: float = 0.0
    weighted_score: float = 0.0
    progress_bonus: float = 0.0
    dangerous_penalty: float = 0.0
    repeated_penalty: float = 0.0
    drift_penalty: float = 0.0
    terminal_bonus: float = 0.0
    total_reward: float = 0.0


class GradingResult(BaseModel):
    """Deterministic output of task graders."""

    model_config = ConfigDict(extra="forbid")

    score: float = Field(..., ge=0.0, le=1.0, description="Score in [0, 1]")
    priority_correct: bool
    category_correct: bool
    action_correct: bool
    priority_component: float
    category_component: float
    action_component: float
    dangerous_penalty: float = 0.0
    repeated_penalty: float = 0.0
    wrong_fields: List[str] = Field(default_factory=list)
    danger_reasons: List[str] = Field(default_factory=list)
    notes: Dict[str, Any] = Field(default_factory=dict)
