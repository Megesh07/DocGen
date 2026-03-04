# ngrok + Ollama Connectivity Verification Report
**Project:** DocGen — Automated Python Docstring Generator  
**Date:** March 4, 2026  
**Purpose:** Verify runtime connectivity for Render FastAPI → ngrok → local Ollama (llama3) chain

---

## Step 1 — Local Ollama

**Status: PASS**

| Check | Result |
|---|---|
| Ollama process running | ✅ PID 25992, listening on `127.0.0.1:11434` |
| `/api/tags` responds | ✅ Valid JSON returned |
| `llama3:latest` installed | ✅ Confirmed in model list |
| Bind address | ⚠️ `127.0.0.1` only (loopback) — not `0.0.0.0` |

The loopback-only bind is **not a problem for ngrok** — ngrok runs on the same machine and can reach `127.0.0.1:11434`. It would only become a problem if Ollama needed to be reachable from a different host directly (e.g. Docker Compose sidecar).

---

## Step 2 — ngrok Tunnel

**Status: FAIL**

| Check | Result |
|---|---|
| ngrok process running | ❌ No `ngrok` process found |
| Port 4040 (ngrok web UI) open | ❌ Not listening |
| HTTPS forwarding URL | ❌ Cannot retrieve — tunnel does not exist |
| `ngrok` binary in PATH | ❌ `Get-Command ngrok` returns nothing |

The terminal context shows `ngrok http 11434` was the last command in the PowerShell Extension terminal, but the process is not active. Either:
- ngrok exited immediately (auth token not configured)
- The binary is not in `PATH`

**To start ngrok correctly:**

```powershell
# If binary is in PATH
ngrok http 11434

# If binary is not in PATH, run from download directory
.\ngrok.exe http 11434
```

A free account and auth token are required on first run:

```powershell
ngrok config add-authtoken <your-token>
```

Tokens are available at [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken).

Once running, the HTTPS forwarding URL will appear in the terminal:

```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:11434
```

Verify connectivity through the tunnel:

```powershell
Invoke-RestMethod -Uri "https://abc123.ngrok-free.app/api/tags"
```

---

## Step 3 — Backend Endpoint Compatibility

**Status: FAIL — critical wiring gap**

| Check | Result |
|---|---|
| Ollama endpoint used | `http://127.0.0.1:11434/api/generate` — correct |
| Timeout | `45.0s` — adequate for llama3:latest |
| HTTPS support | ✅ `httpx` supports HTTPS natively |
| `LLM_BASE_URL` env var wired to provider | ❌ **Not connected** |

### Root Cause

In `src/autodocstring/api/app.py` (line 184), the Ollama provider is instantiated with no arguments:

```python
from autodocstring.generator.ollama_provider import OllamaProvider
return OllamaProvider()
```

`OllamaProvider.__init__` defaults to `url = "http://127.0.0.1:11434/api/generate"`. The `LLM_BASE_URL` environment variable exists in `config/loader.py` but is **never passed** to `OllamaProvider()`.

Setting `LLM_BASE_URL=https://<ngrok-url>` on Render currently has **zero effect** — the backend always tries to reach `127.0.0.1` on the Render server, which does not have Ollama installed.

### Required Fix (single line change in `app.py`)

```python
# Current (broken for cloud deployment)
return OllamaProvider()

# Required (reads LLM_BASE_URL env var)
llm_url = os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434") + "/api/generate"
return OllamaProvider(url=llm_url)
```

This change:
- Defaults to `http://127.0.0.1:11434/api/generate` in local dev (no behavior change)
- Accepts any HTTPS ngrok or remote Ollama URL when `LLM_BASE_URL` is set

---

## Step 4 — Cloud Wiring Readiness

**Status: FAIL**

The intended production chain:

```
Render FastAPI backend
        │
        │  POST {LLM_BASE_URL}/api/generate
        ▼
ngrok HTTPS tunnel  (https://abc123.ngrok-free.app)
        │
        │  forwards to
        ▼
Local Ollama  (127.0.0.1:11434)
        │
        ▼
llama3:latest generates summary sentence
```

This chain **cannot work until the `OllamaProvider` wiring fix is applied** (Step 3).

### Render Environment Variable Setup (after fix)

In Render dashboard → Environment → Add environment variable:

| Variable | Value |
|---|---|
| `LLM_BASE_URL` | `https://abc123.ngrok-free.app` |
| `LLM_MODEL` | `llama3:latest` |

**Important:** ngrok free tier generates a **new URL on every restart**. The Render env var must be updated each time ngrok is restarted. For a stable demo, use a paid ngrok plan with a fixed domain, or keep `ngrok http 11434` running continuously throughout the demo session.

---

## Full Verification Summary

| Check | Status | Blocking |
|---|---|---|
| Local Ollama running | ✅ PASS | — |
| `llama3:latest` present | ✅ PASS | — |
| ngrok process running | ❌ FAIL | Yes — tunnel does not exist |
| `ngrok` binary in PATH | ❌ FAIL | Yes — cannot start without installing it |
| `LLM_BASE_URL` wired to `OllamaProvider` | ❌ FAIL | Yes — env var silently ignored |
| Timeout adequate for llama3 | ✅ PASS (45 s) | — |
| httpx supports HTTPS | ✅ PASS | — |

---

## Final Verdict: NOT READY for live demo via ngrok

**Two blockers must be resolved:**

### Blocker 1 — ngrok not running

Install ngrok, configure auth token, and start the tunnel:

```powershell
ngrok config add-authtoken <token>
ngrok http 11434
```

### Blocker 2 — `LLM_BASE_URL` not wired to `OllamaProvider`

Apply the one-line fix in `src/autodocstring/api/app.py`:

```python
llm_url = os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434") + "/api/generate"
return OllamaProvider(url=llm_url)
```

Then set `LLM_BASE_URL=https://<ngrok-url>` in the Render environment variables.

---

Once both blockers are resolved, the architecture is fully compatible:
- `httpx` handles HTTPS without any additional configuration
- The `/api/generate` endpoint path is correct for Ollama
- The 45 s timeout is sufficient for llama3:latest on typical hardware
- Ollama's loopback bind does not interfere with ngrok tunneling
