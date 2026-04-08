from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field

from .models import (
    ActionLabel,
    AttachmentMetadata,
    CategoryLabel,
    PriorityLabel,
    ThreadMessage,
)


class ExpectedTriage(BaseModel):
    priority: PriorityLabel
    category: CategoryLabel
    action: ActionLabel


class EmailSample(BaseModel):
    email_id: str
    subject: str
    sender: str
    email_body: str
    timestamp: str
    thread_history: List[ThreadMessage] = Field(default_factory=list)
    attachments: List[AttachmentMetadata] = Field(default_factory=list)
    expected: ExpectedTriage
    risk_tags: List[str] = Field(default_factory=list)
    unsafe_if_ignored: bool = False
    unsafe_if_reply: bool = False
    unsafe_if_forward: bool = False


class TaskDefinition(BaseModel):
    task_id: str
    task_name: str
    difficulty: str
    description: str
    max_steps: int = 6
    instruction: str
    samples: List[EmailSample]


TASK_REGISTRY: Dict[str, TaskDefinition] = {
    "task_1_easy_spam_detection": TaskDefinition(
        task_id="task_1_easy_spam_detection",
        task_name="Easy Spam Detection",
        difficulty="easy",
        description="Clear spam patterns: lottery, fake offers, clickbait discounts.",
        max_steps=5,
        instruction=(
            "Classify obvious spam emails. Expected policy behavior is "
            "low priority + spam category + ignore action."
        ),
        samples=[
            EmailSample(
                email_id="easy-spam-001",
                subject="CONGRATS!! You won 5,00,000 lottery cash today",
                sender="LuckyDraw Global <winners@luckyzz-prize.biz>",
                email_body=(
                    "Dear user, claim ur reward in 15 mins. Send Aadhaar + bank details now. "
                    "No kidding, 100% legit!!!"
                ),
                timestamp="2026-04-07T09:12:00Z",
                expected=ExpectedTriage(priority="low", category="spam", action="ignore"),
                risk_tags=["lottery", "scam", "urgent-pressure"],
                unsafe_if_reply=True,
                unsafe_if_forward=True,
            ),
            EmailSample(
                email_id="easy-spam-002",
                subject="Flash SALE 95% OFF: iPhone only for first 10 ppl",
                sender="Dealz Zone <promo@deals-now-now.click>",
                email_body=(
                    "Hurry yaar, final 7 units left. Pay token in crypto and lock ur order. "
                    "Link expires in 08 min."
                ),
                timestamp="2026-04-07T09:45:00Z",
                expected=ExpectedTriage(priority="low", category="spam", action="ignore"),
                risk_tags=["ad", "fake-offer"],
                unsafe_if_reply=True,
            ),
            EmailSample(
                email_id="easy-spam-003",
                subject="Re: payroll update required immediately",
                sender="HR Portal Support <hr-verify@secure-payroll-update.co>",
                email_body=(
                    "Your salary may be paused. Verify employee password reset with attached form. "
                    "Do not call office."
                ),
                timestamp="2026-04-07T10:03:00Z",
                attachments=[
                    AttachmentMetadata(
                        file_name="salary_verification_form.zip",
                        mime_type="application/zip",
                        size_kb=612,
                    )
                ],
                expected=ExpectedTriage(priority="low", category="spam", action="ignore"),
                risk_tags=["credential-theft", "impersonation"],
                unsafe_if_reply=True,
                unsafe_if_forward=True,
            ),
            EmailSample(
                email_id="easy-spam-004",
                subject="Make money from home in 2 hrs/day!!!",
                sender="Fast Career AI <jobs@instant-income.work>",
                email_body=(
                    "No interview no skill. Earn 50k per week, bas join now and pay registration." 
                    "Reply YES to enroll."
                ),
                timestamp="2026-04-07T10:16:00Z",
                expected=ExpectedTriage(priority="low", category="spam", action="ignore"),
                risk_tags=["job-scam"],
                unsafe_if_reply=True,
            ),
            EmailSample(
                email_id="easy-spam-005",
                subject="Buy followers instantly, 10k for Rs99",
                sender="Growth Booster <promo@growthboost-ads.io>",
                email_body=(
                    "Trusted by creators. Limited coupon HYPE99. Click fast else coupon dead ho jayega."
                ),
                timestamp="2026-04-07T10:40:00Z",
                expected=ExpectedTriage(priority="low", category="spam", action="ignore"),
                risk_tags=["promotion", "ad"],
            ),
        ],
    ),
    "task_2_medium_work_prioritization": TaskDefinition(
        task_id="task_2_medium_work_prioritization",
        task_name="Medium Work Prioritization",
        difficulty="medium",
        description="Work emails where urgency and next action must be inferred correctly.",
        max_steps=6,
        instruction=(
            "Prioritize and categorize work emails with realistic urgency. "
            "Avoid unsafe low-priority handling for time-critical requests."
        ),
        samples=[
            EmailSample(
                email_id="med-work-001",
                subject="Need revised Q2 report before 11:30 standup",
                sender="Riya PM <riya.p@acme.co>",
                email_body=(
                    "Hey, meeting in 30 mins. Please send the final KPI sheet ASAP. "
                    "Client deck is blocked till your update arrives."
                ),
                timestamp="2026-04-07T08:58:00Z",
                expected=ExpectedTriage(priority="high", category="work", action="reply"),
                risk_tags=["deadline", "client-impact"],
                unsafe_if_ignored=True,
            ),
            EmailSample(
                email_id="med-work-002",
                subject="SEV2 prod latency spike - oncall support required",
                sender="SRE Alerting <alerts@sre.acme.co>",
                email_body=(
                    "P95 latency crossed 4s in eu-west. Need incident commander confirmation in next 10 min."
                ),
                timestamp="2026-04-07T11:02:00Z",
                expected=ExpectedTriage(priority="high", category="work", action="escalate"),
                risk_tags=["incident", "production", "urgent"],
                unsafe_if_ignored=True,
            ),
            EmailSample(
                email_id="med-work-003",
                subject="Payroll clarification for contractor invoice",
                sender="Finance Ops <finops@acme.co>",
                email_body=(
                    "Can you forward this thread to payroll team with your manager in CC? "
                    "No immediate urgency but needed today EOD."
                ),
                timestamp="2026-04-07T12:21:00Z",
                expected=ExpectedTriage(priority="medium", category="work", action="forward"),
                risk_tags=["cross-team"],
            ),
            EmailSample(
                email_id="med-work-004",
                subject="Reminder: sprint retro notes pending",
                sender="Scrum Bot <noreply@scrum.acme.co>",
                email_body=(
                    "Retro notes are pending from your side. Pls update by tomorrow morning, thanks."
                ),
                timestamp="2026-04-07T13:10:00Z",
                expected=ExpectedTriage(priority="medium", category="work", action="reply"),
                risk_tags=["routine"],
            ),
            EmailSample(
                email_id="med-work-005",
                subject="FYI: New cafeteria vendor announcement",
                sender="Workplace Admin <workplace@acme.co>",
                email_body=(
                    "Sharing this for your team visibility. If useful, please forward in your team channel."
                ),
                timestamp="2026-04-07T14:45:00Z",
                expected=ExpectedTriage(priority="low", category="work", action="forward"),
                risk_tags=["informational"],
            ),
        ],
    ),
    "task_3_hard_context_reasoning": TaskDefinition(
        task_id="task_3_hard_context_reasoning",
        task_name="Hard Context and Reasoning",
        difficulty="hard",
        description=(
            "Ambiguous scenarios requiring thread interpretation, phishing awareness, and indirect urgency reasoning."
        ),
        max_steps=8,
        instruction=(
            "Use both current email and thread history. Detect phishing, escalation risk, and implied urgency."
        ),
        samples=[
            EmailSample(
                email_id="hard-ctx-001",
                subject="Re: KYC revalidation pending - account suspend in 2 hrs",
                sender="Axis Safe Desk <noreply@axis-verify-security.co>",
                email_body=(
                    "Dear customer, complete KYC now using attached form else account freeze. "
                    "Do not contact branch due maintenance."
                ),
                timestamp="2026-04-07T15:20:00Z",
                thread_history=[
                    ThreadMessage(
                        sender="Axis Bank Official <alerts@axisbank.com>",
                        subject="Monthly statement generated",
                        body="Your statement is available in netbanking.",
                        timestamp="2026-03-31T06:00:00Z",
                    )
                ],
                attachments=[
                    AttachmentMetadata(
                        file_name="KYC_update.xlsm",
                        mime_type="application/vnd.ms-excel.sheet.macroEnabled.12",
                        size_kb=241,
                    )
                ],
                expected=ExpectedTriage(priority="high", category="spam", action="escalate"),
                risk_tags=["phishing", "finance", "impersonation"],
                unsafe_if_reply=True,
                unsafe_if_forward=True,
                unsafe_if_ignored=False,
            ),
            EmailSample(
                email_id="hard-ctx-002",
                subject="Re: Payment API bug still unresolved",
                sender="Nora Patel <nora@northstar-client.com>",
                email_body=(
                    "Third reminder. If this is not fixed today we will escalate to procurement and legal."
                ),
                timestamp="2026-04-07T16:05:00Z",
                thread_history=[
                    ThreadMessage(
                        sender="You <agent@acme.co>",
                        subject="Re: Payment API bug still unresolved",
                        body="We are looking into it and will share ETA soon.",
                        timestamp="2026-04-06T18:20:00Z",
                    ),
                    ThreadMessage(
                        sender="Nora Patel <nora@northstar-client.com>",
                        subject="Re: Payment API bug still unresolved",
                        body="Issue impacts checkout conversion heavily.",
                        timestamp="2026-04-07T09:10:00Z",
                    ),
                ],
                expected=ExpectedTriage(priority="high", category="work", action="escalate"),
                risk_tags=["client-escalation", "revenue-impact"],
                unsafe_if_ignored=True,
            ),
            EmailSample(
                email_id="hard-ctx-003",
                subject="Quick one before APAC wakes up",
                sender="Arjun Director <arjun.d@acme.co>",
                email_body=(
                    "No panic, but can you send me the final security summary tonight itself? "
                    "Need it before 5 AM SG time."
                ),
                timestamp="2026-04-07T21:35:00Z",
                thread_history=[
                    ThreadMessage(
                        sender="Arjun Director <arjun.d@acme.co>",
                        subject="Security summary draft",
                        body="Draft looked good, final pending one incident note.",
                        timestamp="2026-04-07T19:05:00Z",
                    )
                ],
                expected=ExpectedTriage(priority="high", category="work", action="reply"),
                risk_tags=["indirect-urgency"],
                unsafe_if_ignored=True,
            ),
            EmailSample(
                email_id="hard-ctx-004",
                subject="Family: rent transfer by tomorrow pls",
                sender="Maa <mom.personal@mail.com>",
                email_body=(
                    "Beta, landlord ko kal subah transfer karna hai. Call me when free, no stress."
                ),
                timestamp="2026-04-07T18:02:00Z",
                expected=ExpectedTriage(priority="medium", category="personal", action="reply"),
                risk_tags=["personal"],
            ),
            EmailSample(
                email_id="hard-ctx-005",
                subject="Invoice mismatch in vendor payout run",
                sender="Treasury Ops <treasury@acme.co>",
                email_body=(
                    "Need your review on attached payout sheet. Could impact month-end close if delayed."
                ),
                timestamp="2026-04-07T17:14:00Z",
                attachments=[
                    AttachmentMetadata(
                        file_name="vendor_payout_diff_apr.csv",
                        mime_type="text/csv",
                        size_kb=98,
                    )
                ],
                expected=ExpectedTriage(priority="high", category="finance", action="forward"),
                risk_tags=["finance", "deadline"],
                unsafe_if_ignored=True,
            ),
            EmailSample(
                email_id="hard-ctx-006",
                subject="Partner offer: 25% off annual seats for your org",
                sender="Vendor Growth <offers@partner-success.io>",
                email_body=(
                    "Hi team, based on last webinar attendance, we can extend promo till Friday. "
                    "Reply to lock discount and free swag."
                ),
                timestamp="2026-04-07T17:55:00Z",
                thread_history=[
                    ThreadMessage(
                        sender="Vendor Success <csm@partner-success.io>",
                        subject="Thanks for joining webinar",
                        body="Happy to support your evaluation journey.",
                        timestamp="2026-03-29T09:00:00Z",
                    )
                ],
                expected=ExpectedTriage(priority="low", category="promotion", action="ignore"),
                risk_tags=["marketing", "promotion"],
            ),
        ],
    ),
}


TASK_ORDER = list(TASK_REGISTRY.keys())


def list_task_ids() -> List[str]:
    return TASK_ORDER.copy()


def get_task(task_id: str) -> TaskDefinition:
    if task_id not in TASK_REGISTRY:
        raise KeyError(f"Unknown task_id: {task_id}")
    return TASK_REGISTRY[task_id]


def choose_task_id(task_id: str | None, reset_counter: int) -> str:
    if task_id:
        if task_id not in TASK_REGISTRY:
            raise KeyError(f"Unknown task_id: {task_id}")
        return task_id
    return TASK_ORDER[reset_counter % len(TASK_ORDER)]


def choose_sample_index(
    sample_count: int,
    reset_counter: int,
    seed: int | None = None,
    sample_index: int | None = None,
) -> int:
    if sample_count <= 0:
        raise ValueError("Task has no samples")
    if sample_index is not None:
        return sample_index % sample_count
    if seed is not None:
        return seed % sample_count
    return reset_counter % sample_count
