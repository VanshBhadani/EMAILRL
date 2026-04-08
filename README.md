---
title: email_triage_env
sdk: docker
app_port: 7860
---

# email_triage_env

A production-style OpenEnv benchmark environment for realistic email triage.

The environment trains and evaluates agents on three connected decisions per email:
- Priority: high, medium, low
- Category: work, spam, personal, finance, promotion
- Action: reply, ignore, forward, escalate

## Real-World Motivation

Enterprise inboxes are noisy and high-risk. A weak policy can:
- Ignore urgent client escalations
- Reply to phishing emails
- Miss operational incidents

This environment simulates those cases with deterministic tasks, noisy text, typos, Hinglish phrases, thread history, and safety penalties.

## OpenEnv API Contract

The environment is exposed through OpenEnv-compatible endpoints:
- POST /reset
- POST /step
- GET /state
- GET /schema
- GET /health

Internally, the core engine in server/env.py implements:
- reset() -> initial observation
- step(action) -> (observation, reward, done, info)
- state() -> environment state

The OpenEnv adapter maps this to the standard server contract.

## Observation Space

Each observation includes:
- email_id
- subject
- sender
- email_body
- timestamp
- thread_history (list)
- attachments (metadata only)
- task_id, task_name, instruction
- remaining_steps
- last_feedback

Noise realism includes:
- Spelling errors
- Informal phrasing
- Hinglish
- Ambiguous context in thread chains

## Action Space

Expected action object:

```json
{
  "priority": "high | medium | low",
  "category": "work | spam | personal | finance | promotion",
  "action": "reply | ignore | forward | escalate"
}
```

## Tasks (Easy -> Hard)

### Task 1: Easy Spam Detection
- Clear spam cues: lottery, fake discounts, impersonation templates
- Expected pattern: spam + low + ignore
- Multiple deterministic examples

### Task 2: Medium Work Prioritization
- Urgency-sensitive work email handling
- Includes incident alerts and deadline-sensitive workflows
- Requires choosing reply vs forward vs escalate correctly

### Task 3: Hard Context + Reasoning
- Thread-dependent reasoning
- Phishing disguised as finance communication
- Client escalation and indirect urgency scenarios
- Multi-field correctness required

## Grading

Every step is graded with fixed deterministic weights:
- Priority correctness: 0.4
- Category correctness: 0.3
- Action correctness: 0.3

Grader output score is clipped to [0, 1].

Dangerous choices are penalized, including:
- Ignoring urgent/sensitive emails
- Replying to suspicious/phishing emails
- Forwarding potentially malicious content

## Reward Shaping

Reward is dense and non-binary. Each step combines:
- Correctness score (partial credit)
- Progress bonus when the agent improves
- Dangerous decision penalties
- Repeated mistake penalties
- Drift penalty when quality degrades
- Terminal bonus/penalty on solve/fail termination

Episodes terminate on:
- Full triage correctness
- Step limit reached (5 to 10, task-configured)

## Determinism and Reproducibility

The environment is deterministic by design:
- Fixed task registry
- Fixed sample ordering
- Seed-aware sample selection
- No stochastic reward branches

Reset supports deterministic task/sample routing via task_id, sample_index, and seed.

## Project Structure

```text
email_triage_env/
├── openenv.yaml
├── server/
│   ├── env.py
│   ├── models.py
│   ├── tasks.py
│   ├── graders.py
│   └── main.py
├── inference.py
├── Dockerfile
├── requirements.txt
└── README.md
```

Additional compatibility files are included for OpenEnv local validation:
- pyproject.toml
- uv.lock
- client.py
- models.py
- __init__.py

## Setup

### Local Python Setup

```bash
python -m venv .venv
# Windows PowerShell:
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

### Run Server Locally

```bash
uv run server
```

Server starts at:
- http://localhost:7860

### Quick Endpoint Checks

```bash
curl http://localhost:7860/health
curl -X POST http://localhost:7860/reset -H "Content-Type: application/json" -d "{\"task_id\":\"task_1_easy_spam_detection\"}"
```

## Docker

Build:

```bash
docker build -t email-triage-env:latest .
```

Run:

```bash
docker run --rm -p 7860:7860 email-triage-env:latest
```

Container command uses:
- uv run server

## Hugging Face Spaces Deployment Notes

This repository is docker-ready for HF Spaces:
- Dockerfile included
- OpenEnv manifest included
- App listens on port 7860
- POST /reset is available through OpenEnv routes

## Baseline Inference Script

File:
- inference.py

Reads required environment variables:
- API_BASE_URL
- MODEL_NAME
- HF_TOKEN

Optional:
- ENV_BASE_URL (defaults to http://localhost:7860)

Run:

```bash
$env:API_BASE_URL = "https://your-openai-compatible-endpoint/v1"
$env:MODEL_NAME = "your-model"
$env:HF_TOKEN = "your-token"
python inference.py --env-url http://localhost:7860
```

## Required Logging Format

inference.py emits strict lines:

```text
[START] task=task_1_easy_spam_detection env=http://localhost:7860 model=your-model
[STEP] step=1 action={"priority":"low","category":"spam","action":"ignore"} reward=1.00 done=true error=null
[END] success=true steps=1 score=1.00 rewards=[1.00]
```

Formatting guarantees:
- reward has 2 decimals
- done is true/false lowercase
- error is null when no error
- score is clipped to [0, 1]

## Baseline Scores

Deterministic baseline scores on bundled samples (computed from server/graders.py):

| Baseline policy | Task 1 avg | Task 2 avg | Task 3 avg | Overall avg | Task success rates (T1/T2/T3) |
|---|---:|---:|---:|---:|---|
| Safe default (`low/spam/ignore`) | 1.00 | 0.08 | 0.17 | 0.40 | 1.00 / 0.00 / 0.00 |
| Keyword heuristic (non-LLM) | 0.80 | 0.86 | 0.82 | 0.83 | 0.80 / 0.80 / 0.67 |

For model-based baselines, run inference.py with your API-compatible model and capture per-task END lines.

## Production Notes

- Typed Pydantic contracts for action, observation, reward breakdown
- Safety-aware grader penalties
- Thread-aware hard task examples
- Deterministic evaluation for benchmark reproducibility
