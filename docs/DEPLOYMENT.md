# Deployment Guide — DocGen

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| Python | 3.8 | 3.11 recommended; tested in CI with 3.11 |
| pip | 22+ | ships with Python 3.11 |
| Node.js | 18 LTS | for the React frontend |
| npm | 9+ | included with Node.js 18 |
| Git | any | for cloning |

---

## 1. Environment Variables

Create a `.env` file in the repository root (it is gitignored). Only `GROQ_API_KEY` is optional — the application runs entirely offline without it (template-only docstrings).

```env
# ── LLM Integration (optional) ──────────────────────────────────
GROQ_API_KEY=gsk_...          # From https://console.groq.com/keys

# ── Backend settings (optional overrides) ───────────────────────
ALLOWED_ORIGINS=http://localhost:5173   # Comma-separated CORS origins
SESSION_DIR=.autodocstring_sessions     # Where session files are stored
SESSION_TTL_HOURS=2                     # Session auto-cleanup (hours)
LLM_MODEL=llama-3.3-70b-versatile      # Groq model name
LLM_TIMEOUT=45                          # Groq request timeout (seconds)
```

> **Never commit your `GROQ_API_KEY`.** The `.gitignore` already protects `.env`, `.env.local`, and `.env.*.local`. See [SECURITY.md](SECURITY.md) for details.

---

## 2. Backend Setup

### 2a. Install Python dependencies

```bash
# From repository root
pip install -e .
```

This installs `autodocstring` in editable mode along with all runtime dependencies declared in `pyproject.toml`:

- `fastapi`
- `uvicorn[standard]`
- `pydantic>=2.0`
- `jinja2`
- `pydocstyle`
- `rich`
- `tabulate`
- `httpx` (Groq HTTP client)

### 2b. Start the backend server

```bash
uvicorn autodocstring.api.app:app \
    --reload \
    --port 8001 \
    --app-dir src
```

The API will be available at `http://localhost:8001`. You can verify it is running:

```bash
curl http://localhost:8001/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "llm_available": true,
  "session_count": 0,
  "uptime_seconds": 12
}
```

If `llm_available` is `false`, the `GROQ_API_KEY` is not set — docstrings will still be generated using the deterministic template engine.

---

## 3. Frontend Setup

### 3a. Install Node dependencies

```bash
cd project/frontend
npm install
```

### 3b. Configure the API URL

The frontend reads `VITE_API_BASE` to locate the backend:

```bash
# project/frontend/.env.development  (already present in repo)
VITE_API_BASE=http://localhost:8001/api/v1
```

You do not need to edit this for local development.

### 3c. Start the dev server

```bash
cd project/frontend
npm run dev
```

The app will be available at `http://localhost:5173`.

---

## 4. Verifying the Full Stack

1. Open `http://localhost:5173` in a browser.
2. Upload the demo file `demo/01_no_docstrings/calculator.py`.
3. Select **Google** style and click **Analyze**.
4. Click **Generate Docstrings**.
5. Review the diff in the Review phase.
6. Download the documented file.

If any phase fails, check the browser console and the uvicorn terminal for errors.

---

## 5. Production Deployment

### 5a. Build the frontend

```bash
cd project/frontend
npm run build
```

This produces a `project/frontend/dist/` directory containing static HTML/JS/CSS.

### 5b. Serve static files with FastAPI

The FastAPI app can serve the built frontend directly:

```python
# Already implemented in app.py when SERVE_STATIC=1
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="project/frontend/dist", html=True))
```

Set `SERVE_STATIC=1` and point the dist path to your build output.

### 5c. Run without `--reload` in production

```bash
uvicorn autodocstring.api.app:app \
    --host 0.0.0.0 \
    --port 8001 \
    --workers 2 \
    --app-dir src
```

> Do **not** use `--reload` in production — it adds file-system watchers and crashes on code errors.

### 5d. Reverse proxy (nginx example)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Frontend static files
    location / {
        root /var/www/docgen/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Remember to set `ALLOWED_ORIGINS=https://yourdomain.com` so CORS allows the browser to call the backend.

---

## 6. Remote LLM Access (Groq Cloud)

If deploying on a VM without internet access to Groq, you can tunnel using ngrok:

```bash
ngrok http 8001
```

See [docs/NGROK_OLLAMA_REPORT.md](NGROK_OLLAMA_REPORT.md) for the detailed setup that was used during Infosys evaluation.

---

## 7. GitHub Actions CI

The workflow at `.github/workflows/ci.yml` runs automatically on every `push` and `pull_request`:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest --tb=short
```

### Running CI locally

```bash
# Install dev extras (pytest, pytest-cov, black, mypy, flake8)
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=src/autodocstring --cov-report=term-missing
```

---

## 8. Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| `uvicorn: command not found` | Package not installed | `pip install -e .` from repo root |
| `Module autodocstring not found` | Wrong `--app-dir` | Must pass `--app-dir src` |
| `CORS blocked in browser` | `ALLOWED_ORIGINS` mismatch | Set `ALLOWED_ORIGINS=http://localhost:5173` |
| Frontend shows "Cannot connect to backend" | Backend not running | Start uvicorn first |
| `npm install` fails | Old Node.js | Upgrade to Node.js 18 LTS |
| `GROQ_API_KEY invalid` | Wrong key format | Keys start with `gsk_`; copy from Groq console |
| Sessions not cleaned up | `SESSION_TTL_HOURS` too high | Lower TTL or manually delete `.autodocstring_sessions/` |
