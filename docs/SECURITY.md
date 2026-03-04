# Security Guide — DocGen

## 1. Secret Management

### API Keys

DocGen uses two optional external credentials:

| Secret           | Used For                                 | Where to Store                |
| ---------------- | ---------------------------------------- | ----------------------------- |
| `GROQ_API_KEY`   | Groq LLM API (summary generation)        | `.env` file or Render env var |
| `GEMINI_API_KEY` | Google Gemini LLM (alternative provider) | `.env` file or Render env var |

**Rules:**

- Store secrets **only** in `.env` (local) or in your hosting dashboard (cloud)
- Never hardcode them in source code or commit messages
- Never log them — the backend strips API keys from all error responses
- Rotate immediately if exposed: [console.groq.com/keys](https://console.groq.com/keys)

**Gitignore protection** (already configured):

```gitignore
.env
.env.local
.env.*.local
**/.env.local
**/.env.*.local
```

### Checking for accidental commits

```bash
git log -p | grep -E "(GROQ_API_KEY|GEMINI_API_KEY|gsk_)[^\s]+"
```

If found, rotate immediately and rewrite history with `git filter-repo` or BFG Repo-Cleaner.

---

## 2. CORS Configuration

CORS is enforced by FastAPI middleware in `app.py`:

```python
_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Local development (default):**

```env
ALLOWED_ORIGINS=http://localhost:5173
```

**Production (Render → Vercel):**

```env
ALLOWED_ORIGINS=https://doc-gen-fo6v.vercel.app
```

> Never use `*` as `ALLOWED_ORIGINS` in production — it allows any website to call your API.

---

## 3. Path Sandbox — `_resolve_safe_path`

All endpoints that accept a file path parameter (`/preview`, `/file`, `/save_file`) pass it through `_resolve_safe_path()`:

```python
def _resolve_safe_path(raw_path: str) -> Path:
    resolved = Path(raw_path).resolve()

    # Allow paths under the app's project root
    in_project = False
    try:
        resolved.relative_to(PROJECT_ROOT)
        in_project = True
    except ValueError:
        pass

    # Also allow paths under the session directory (which may be /tmp on cloud)
    if not in_project:
        try:
            resolved.relative_to(_SESSIONS_ROOT)
            in_project = True
        except ValueError:
            pass

    if not in_project:
        raise HTTPException(status_code=403, detail="Access denied")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    return resolved
```

**Why two roots?** On Render, `SESSION_DIR` is set to `/tmp`, which is outside the app's working directory (`PROJECT_ROOT`). Files uploaded by users are stored in the session workspace under `_SESSIONS_ROOT` (`/tmp`). Without allowing `_SESSIONS_ROOT`, every `/preview` and `/file` request would return 403.

**Security guarantee:** A caller cannot supply a path like `/etc/passwd` or `../../secret` because `Path.resolve()` normalises all traversal sequences before the prefix check is applied.

---

## 4. File Upload Security

Uploaded files are:

1. **Extension-validated** — only `.py` files are accepted; others are silently skipped
2. **Sanitized** — filenames have leading `/`/`\` and `..` sequences stripped before saving:
   ```python
   safe_rel_path = upload.filename.lstrip("/\\").replace("..", "")
   ```
3. **Stored in a session-scoped directory** — `_SESSIONS_DIR/<session_id>/workspace/`
4. **Never executed** — files are parsed only with Python's `ast` module; no `exec`, `eval`, or subprocess calls

---

## 5. Session Isolation

Each upload creates a UUID v4 session. Session directories are stored at:

```
_SESSIONS_DIR/
└── <session-id>/
    └── workspace/         ← uploaded .py files
```

Batch snapshots (created during generation for undo/cancel support):

```
_SESSIONS_DIR/
└── <batch-id>/
    └── <md5hash>_<filename>  ← snapshot copies
```

**Isolation guarantees:**

- Sessions are completely independent — one session cannot read or write another session's files
- Session IDs are UUID v4 (cryptographically random); enumeration is infeasible
- Session IDs are generated server-side and returned only to the requesting browser
- Expired sessions are purged by a background task every 30 minutes

---

## 6. No Persistent User Data

DocGen **does not store user data permanently**:

- Sessions auto-expire after `SESSION_TTL_HOURS` (default: 2 hours)
- No user accounts, no authentication, no database
- Groq receives only the **function signature** (name, parameter names, return type) — never the function body, variable names, comments, or business logic

---

## 7. LLM Prompt Safety

The prompt sent to any LLM provider is strictly controlled:

```python
# Only this leaves your machine
f"Write a single-sentence Python docstring summary for: {func_signature}"
# Example: "Write a single-sentence Python docstring summary for: calculate_tax(income: float, rate: float) -> float"
```

No source code body, no docstrings, no variable names from the function body are included. This ensures:

- No leakage of business logic or proprietary variable names
- The LLM cannot hallucinate parameter names because it is not given the body
- If the LLM returns malformed output, only the summary placeholder is affected; all structured sections (Args, Returns, Raises) are template-rendered

---

## 8. Syntax Safety

The `_insert_docstrings()` applier re-parses every file with `ast.parse()` after writing. If the generated docstring causes a syntax error (defensive check — should not happen under normal operation), the original file content is **automatically restored** before the error is returned to the caller.

A malformed LLM or template response can never corrupt the user's source file.

---

## 9. Dependency Auditing

```bash
# Python
pip install pip-audit
pip-audit

# Frontend
cd project/frontend
npm audit
```

Keep `package-lock.json` committed so dependency trees are reproducible across environments.

---

## 10. Pre-commit Hook (Optional)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: autodocstring-check
        name: Docstring coverage check
        entry: python -m autodocstring precommit
        language: python
        types: [python]
```

---

## 11. Security Checklist for Production Deployment

- [ ] `GROQ_API_KEY` / `GEMINI_API_KEY` set via env var, not in source code
- [ ] `.env` is NOT committed
- [ ] `ALLOWED_ORIGINS` set to exact production frontend URL (not `*`)
- [ ] `SESSION_DIR` set to a writable directory (e.g. `/tmp` on Render)
- [ ] `SESSION_TTL_HOURS` ≤ 24
- [ ] `--reload` removed from uvicorn command
- [ ] Backend behind HTTPS (Render handles this automatically)
- [ ] `npm audit` — 0 critical/high issues
- [ ] `pip-audit` — no known vulnerabilities
