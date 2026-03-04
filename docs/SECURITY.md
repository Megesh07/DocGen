# Security Guide — DocGen

## 1. Secret Management

### GROQ_API_KEY

The Groq API key is the only external credential this application uses.

**Rules:**
- Store it **only** in a `.env` file in the repository root
- Never hardcode it in source code, configuration files, or commit messages
- Never log it — the backend strips API keys from all error messages before returning responses
- Rotate it immediately if you suspect it was exposed — visit [console.groq.com/keys](https://console.groq.com/keys)

**Gitignore protection** (already configured in `.gitignore`):

```gitignore
.env
.env.local
.env.*.local
**/.env.local
**/.env.*.local
```

If you add additional secrets (e.g., a database URL, another LLM key), add them to `.env` and verify the above patterns cover them.

### Checking for accidental commits

If you suspect a secret was committed:

```bash
# Search all commits for common secret patterns
git log -p | grep -E "(GROQ_API_KEY|gsk_|sk-)[^\s]+"
```

If found, rotate the key immediately and use `git filter-repo` or BFG Repo-Cleaner to rewrite history.

---

## 2. CORS Configuration

Cross-Origin Resource Sharing (CORS) is enforced by FastAPI middleware in `app.py`.

**Default (development):**
```
ALLOWED_ORIGINS=http://localhost:5173
```

**Production:** Set `ALLOWED_ORIGINS` to your exact frontend domain:
```env
ALLOWED_ORIGINS=https://yourdomain.com
```

Never use `*` (wildcard) as `ALLOWED_ORIGINS` in production — it allows any website to call your backend API.

The CORS configuration in `app.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # from env var
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 3. Input Validation

All API request bodies are validated by **Pydantic v2 models** defined in `src/autodocstring/api/schemas.py`. Pydantic rejects requests that:
- Contain fields of the wrong type
- Are missing required fields
- Contain values outside allowed ranges

### Docstring style input

The `style` parameter is sanitized via `_normalize_style()` before use — only the values `google`, `numpy`, `rest`, `epytext`, and `sphinx` are accepted. Any other value is rejected with `HTTP 422 Unprocessable Entity`.

### File upload

Uploaded files are:
1. Validated to have a `.py` extension before saving
2. Written to a session-scoped directory, not the system temp directory
3. Never executed — they are only parsed with Python's `ast` module

---

## 4. Session Isolation

Each upload creates a **UUID-based session** (e.g., `3b7a1f22-ec4a-4d8a-9d6b-...`). Session directories are stored at:

```
.autodocstring_sessions/
└── <session-id>/
    ├── original/   ← unmodified uploaded files
    └── current/    ← working copies (apply/undo affects these only)
```

**Isolation guarantees:**
- Sessions are independent — one session cannot read or write another session's files
- Session IDs are UUIDs (Version 4, cryptographically random), making enumeration infeasible
- The session ID is generated server-side and returned to the browser on session creation

---

## 5. No Persistent User Data

DocGen **does not store user data permanently**:

- Sessions are cleaned up automatically after `SESSION_TTL_HOURS` (default: 2 hours)
- No user accounts, no authentication tokens, no uploaded file content is written to a database
- Groq receives only the **function signature** (name, parameter names, return type) — the function body and any comments in the source code are never sent to external APIs

---

## 6. LLM Prompt Safety

The prompt sent to Groq is strictly controlled:

```python
# Only this information leaves your machine
f"Write a single-sentence Python docstring summary for: {func_signature}"
# Example: "Write a single-sentence Python docstring summary for: calculate_tax(income: float, rate: float) -> float"
```

No source code, no docstrings, no variable names from the function body are included in the prompt. This ensures:
- No accidental leakage of business logic or private variable names to the LLM provider
- The LLM cannot hallucinate parameter names because it is not given the body

---

## 7. Syntax Safety

The `SafeApplier` re-parses every file with `ast.parse()` after writing. If the generated docstring causes a syntax error (which should not happen under normal conditions but is defensively checked), the original file content is **automatically restored** before any error is returned to the caller.

This means a malformed LLM response can never corrupt the user's source file.

---

## 8. Dependency Security

Run a pip audit to check for known vulnerabilities:

```bash
pip install pip-audit
pip-audit
```

Frontend dependencies can be audited with:

```bash
cd project/frontend
npm audit
```

Keep dependencies up to date. The lockfile (`package-lock.json`) is committed so frontend dependency trees are reproducible.

---

## 9. Pre-commit Hook (Optional)

The integration module `src/autodocstring/integrations/precommit.py` provides a pre-commit hook that scans staged `.py` files before every commit. This is useful for enforcing docstring coverage on a team:

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

## 10. Security Checklist for Deployment

Before going to production, verify:

- [ ] `GROQ_API_KEY` is set via environment variable, not hardcoded  
- [ ] `.env` file is NOT committed to the repository  
- [ ] `ALLOWED_ORIGINS` is set to the exact production frontend URL (not `*`)  
- [ ] `SESSION_TTL_HOURS` is configured to a reasonable value (≤24 h)  
- [ ] `--reload` flag is removed from the uvicorn command  
- [ ] Backend is behind a reverse proxy (nginx/caddy) — do not expose uvicorn directly  
- [ ] HTTPS is terminated at the reverse proxy  
- [ ] `npm audit` shows 0 critical/high vulnerabilities  
- [ ] `pip-audit` shows no known vulnerable packages  
