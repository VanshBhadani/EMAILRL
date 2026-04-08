from __future__ import annotations

import os

from openenv.core.env_server import create_app

try:
    from .env import EmailTriageEnvironment
    from .models import EmailTriageAction, EmailTriageObservation
except ImportError:
    from env import EmailTriageEnvironment
    from models import EmailTriageAction, EmailTriageObservation


MAX_CONCURRENT_ENVS = int(os.getenv("MAX_CONCURRENT_ENVS", "1"))

_SHARED_ENV = EmailTriageEnvironment()


def create_email_triage_environment() -> EmailTriageEnvironment:
    return _SHARED_ENV

app = create_app(
    create_email_triage_environment,
    EmailTriageAction,
    EmailTriageObservation,
    env_name="email_triage_env",
    max_concurrent_envs=max(1, MAX_CONCURRENT_ENVS),
)


def main(host: str = "0.0.0.0", port: int | None = None) -> None:
    import uvicorn

    if port is None:
        port = int(os.getenv("PORT", "7860"))

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
