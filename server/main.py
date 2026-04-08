from __future__ import annotations

import json
import os

from fastapi.responses import HTMLResponse
from openenv.core.env_server import create_app

try:
    from .env import EmailTriageEnvironment
    from .models import EmailTriageAction, EmailTriageObservation
    from .tasks import list_task_ids
except ImportError:
    from env import EmailTriageEnvironment
    from models import EmailTriageAction, EmailTriageObservation
    from tasks import list_task_ids


MAX_CONCURRENT_ENVS = int(os.getenv("MAX_CONCURRENT_ENVS", "1"))
TASK_IDS = list_task_ids()

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


def _root_metadata() -> dict[str, object]:
    return {
        "name": "email_triage_env",
        "status": "running",
                "message": "OpenEnv server is live. Open '/' for interactive demo UI.",
        "docs": "/docs",
        "health": "/health",
                "ui": "/",
        "endpoints": {
            "reset": "POST /reset",
            "step": "POST /step",
            "state": "GET /state",
            "schema": "GET /schema",
        },
                "tasks": TASK_IDS,
    }


def _build_root_html() -> str:
        template = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Email Triage RL Demo</title>
    <style>
        :root {
            --bg: #0a111f;
            --panel: #101a2f;
            --panel-2: #0f2740;
            --accent: #4cc9f0;
            --accent-2: #f59e0b;
            --ok: #34d399;
            --text: #eaf2ff;
            --muted: #95a8c6;
            --danger: #f87171;
            --border: #264266;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: "Segoe UI", Tahoma, sans-serif;
            color: var(--text);
            background: radial-gradient(1200px 600px at 20% -20%, #1b3358 0%, var(--bg) 50%), var(--bg);
        }
        .wrap {
            max-width: 1100px;
            margin: 24px auto;
            padding: 16px;
        }
        .hero {
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 18px;
            background: linear-gradient(145deg, #142640, #0d1a30 55%);
        }
        h1 { margin: 0 0 8px; font-size: 1.5rem; }
        p { margin: 0; color: var(--muted); line-height: 1.4; }
        .grid {
            margin-top: 16px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        .card {
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 14px;
            background: var(--panel);
        }
        label {
            display: block;
            margin: 10px 0 6px;
            color: var(--muted);
            font-size: 0.9rem;
        }
        input, select, button {
            width: 100%;
            border-radius: 10px;
            border: 1px solid var(--border);
            background: var(--panel-2);
            color: var(--text);
            padding: 10px;
            font-size: 0.95rem;
        }
        .row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        button {
            cursor: pointer;
            border: 1px solid #3c6fa0;
            background: linear-gradient(145deg, #1a3d63, #164368);
            transition: transform 0.12s ease, opacity 0.12s ease;
        }
        button:hover { transform: translateY(-1px); }
        .btn-accent {
            border-color: #0d6c82;
            background: linear-gradient(145deg, #0f5f76, #1082a1);
        }
        .btn-warn {
            border-color: #8f5e0a;
            background: linear-gradient(145deg, #7f5a13, #a7781f);
        }
        .pill {
            display: inline-block;
            font-size: 0.8rem;
            margin-top: 10px;
            padding: 4px 8px;
            border-radius: 999px;
            border: 1px solid var(--border);
            color: var(--muted);
        }
        pre {
            margin: 0;
            max-height: 260px;
            overflow: auto;
            border-radius: 10px;
            border: 1px solid var(--border);
            padding: 10px;
            background: #091425;
            color: #d7e9ff;
            font-size: 0.86rem;
            line-height: 1.45;
        }
        .status {
            margin: 10px 0 0;
            font-size: 0.9rem;
            color: var(--muted);
        }
        .ok { color: var(--ok); }
        .danger { color: var(--danger); }
        .meta {
            margin-top: 10px;
            color: var(--muted);
            font-size: 0.85rem;
        }
        @media (max-width: 900px) {
            .grid { grid-template-columns: 1fr; }
            .row { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="wrap">
        <section class="hero">
            <h1>Email Triage RL Live Demo</h1>
            <p>
                This simulates a real human workflow: triaging enterprise email for priority, category, and action.
                Use reset and step to run an episode and observe shaped rewards in real time.
            </p>
            <span class="pill">Environment: email_triage_env</span>
        </section>

        <section class="grid">
            <div class="card">
                <h3 style="margin-top:0;">Episode Control</h3>
                <label for="taskId">Task</label>
                <select id="taskId"></select>

                <div class="row">
                    <div>
                        <label for="sampleIndex">Sample Index (optional)</label>
                        <input id="sampleIndex" type="number" min="0" placeholder="auto" />
                    </div>
                    <div>
                        <label for="seed">Seed (optional)</label>
                        <input id="seed" type="number" min="0" placeholder="auto" />
                    </div>
                </div>

                <div class="row" style="margin-top:12px;">
                    <button id="resetBtn" class="btn-accent">Reset Episode</button>
                    <button id="stateBtn">Fetch State</button>
                </div>

                <h3 style="margin-top:18px;">Agent Action</h3>
                <div class="row">
                    <div>
                        <label for="priority">Priority</label>
                        <select id="priority">
                            <option value="high">high</option>
                            <option value="medium">medium</option>
                            <option value="low" selected>low</option>
                        </select>
                    </div>
                    <div>
                        <label for="category">Category</label>
                        <select id="category">
                            <option value="work">work</option>
                            <option value="spam" selected>spam</option>
                            <option value="personal">personal</option>
                            <option value="finance">finance</option>
                            <option value="promotion">promotion</option>
                        </select>
                    </div>
                </div>

                <label for="action">Action</label>
                <select id="action">
                    <option value="reply">reply</option>
                    <option value="ignore" selected>ignore</option>
                    <option value="forward">forward</option>
                    <option value="escalate">escalate</option>
                </select>

                <div class="row" style="margin-top:12px;">
                    <button id="stepBtn" class="btn-warn">Step</button>
                    <button id="spamPresetBtn">Spam Preset</button>
                </div>

                <p id="status" class="status">Ready.</p>
                <p class="meta">Tip: Use /docs for full API schema, or run your inference.py against this endpoint.</p>
            </div>

            <div class="card">
                <h3 style="margin-top:0;">Observation</h3>
                <pre id="obs">{}</pre>

                <h3>State</h3>
                <pre id="state">{}</pre>

                <h3>Step Log</h3>
                <pre id="log"></pre>
            </div>
        </section>
    </div>

    <script>
        const TASKS = __TASKS__;
        const statusEl = document.getElementById("status");
        const obsEl = document.getElementById("obs");
        const stateEl = document.getElementById("state");
        const logEl = document.getElementById("log");
        const taskSelect = document.getElementById("taskId");
        let currentObservation = null;

        function setStatus(msg, isError = false) {
            statusEl.textContent = msg;
            statusEl.className = "status " + (isError ? "danger" : "ok");
        }

        function appendLog(line) {
            const stamp = new Date().toLocaleTimeString();
            logEl.textContent += `[${stamp}] ${line}\n`;
            logEl.scrollTop = logEl.scrollHeight;
        }

        function setJson(el, obj) {
            el.textContent = JSON.stringify(obj || {}, null, 2);
        }

        async function request(path, method = "GET", body = null) {
            const res = await fetch(path, {
                method,
                headers: { "Content-Type": "application/json" },
                body: body ? JSON.stringify(body) : null,
            });
            const text = await res.text();
            let data = null;
            try { data = text ? JSON.parse(text) : {}; } catch (_) { data = { raw: text }; }
            if (!res.ok) {
                const detail = data && data.detail ? data.detail : text || `HTTP ${res.status}`;
                throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
            }
            return data;
        }

        function currentAction() {
            return {
                priority: document.getElementById("priority").value,
                category: document.getElementById("category").value,
                action: document.getElementById("action").value,
            };
        }

        async function doReset() {
            try {
                const payload = { task_id: taskSelect.value };
                const sampleIndex = document.getElementById("sampleIndex").value.trim();
                const seed = document.getElementById("seed").value.trim();
                if (sampleIndex !== "") payload.sample_index = Number(sampleIndex);
                if (seed !== "") payload.seed = Number(seed);

                const data = await request("/reset", "POST", payload);
                currentObservation = data.observation || null;
                setJson(obsEl, currentObservation || data);
                appendLog(`RESET task=${taskSelect.value}`);
                setStatus("Episode reset successful.");
            } catch (err) {
                setStatus(`Reset failed: ${err.message}`, true);
            }
        }

        async function doStep() {
            try {
                if (!currentObservation) {
                    setStatus("Please reset first.", true);
                    return;
                }
                const action = currentAction();
                const data = await request("/step", "POST", { action });
                currentObservation = data.observation || null;
                setJson(obsEl, currentObservation || data);

                const reward = Number(data.reward || 0).toFixed(2);
                const done = Boolean(data.done);
                const feedback = (currentObservation && currentObservation.last_feedback) || "";
                appendLog(`STEP action=${JSON.stringify(action)} reward=${reward} done=${done} feedback=${feedback}`);
                setStatus(done ? "Episode finished." : "Step completed.");
            } catch (err) {
                setStatus(`Step failed: ${err.message}`, true);
            }
        }

        async function fetchState() {
            try {
                const data = await request("/state", "GET");
                setJson(stateEl, data);
                appendLog("STATE fetched");
                setStatus("State updated.");
            } catch (err) {
                setStatus(`State fetch failed: ${err.message}`, true);
            }
        }

        function applySpamPreset() {
            document.getElementById("priority").value = "low";
            document.getElementById("category").value = "spam";
            document.getElementById("action").value = "ignore";
            setStatus("Applied spam preset action.");
        }

        function initTaskOptions() {
            TASKS.forEach((taskId) => {
                const opt = document.createElement("option");
                opt.value = taskId;
                opt.textContent = taskId;
                taskSelect.appendChild(opt);
            });
        }

        document.getElementById("resetBtn").addEventListener("click", doReset);
        document.getElementById("stepBtn").addEventListener("click", doStep);
        document.getElementById("stateBtn").addEventListener("click", fetchState);
        document.getElementById("spamPresetBtn").addEventListener("click", applySpamPreset);

        initTaskOptions();
        appendLog("UI ready. Start with Reset Episode.");
    </script>
</body>
</html>
"""
        return template.replace("__TASKS__", json.dumps(TASK_IDS, ensure_ascii=True))


@app.get("/", include_in_schema=False)
def root_ui() -> HTMLResponse:
        return HTMLResponse(content=_build_root_html())


@app.get("/api", include_in_schema=False)
def root_api() -> dict[str, object]:
        return _root_metadata()


def main(host: str = "0.0.0.0", port: int | None = None) -> None:
    import uvicorn

    if port is None:
        port = int(os.getenv("PORT", "7860"))

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
