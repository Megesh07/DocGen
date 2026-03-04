# Deployment Guide — DocGen

## Prerequisites

| Requirement | Minimum | Notes                    |
| ----------- | ------- | ------------------------ |
| Python      | 3.11    | Tested in CI with 3.11   |
| pip         | 22+     | ships with Python 3.11   |
| Node.js     | 18 LTS  | for the React frontend   |
| npm         | 9+      | included with Node.js 18 |
| Git         | any     | for cloning              |

---

## 1. Environment Variables

Create a `.env` file in the repository root (it is gitignored).

```env
# ── LLM Integration (optional) ──────────────────────────────────
GROQ_API_KEY=gsk_...              # From https://console.groq.com/keys
GEMINI_API_KEY=...                # Google AI Studio (optional alternative)

# ── Backend settings ─────────────────────────────────────────────
ALLOWED_ORIGINS=http://localhost:5173   # Comma-separated CORS origins
SESSION_DIR=.autodocstring_sessions     # Where session workspace dirs are stored
                                        # On Render set to /tmp for writable disk
SESSION_TTL_HOURS=2                     # Auto-cleanup TTL (hours)
LLM_MODEL=llama-3.3-70b-versatile      # Groq model
LLM_TIMEOUT=45                          # Groq request timeout (seconds)
LLM_BASE_URL=http://127.0.0.1:11434    # Ollama base URL (local LLM fallback)
```

> **Never commit your `GROQ_API_KEY`.** The `.gitignore` already protects `.env`. See [SECURITY.md](SECURITY.md).

**Provider auto-selection logic:**

1. If `GROQ_API_KEY` is set → use Groq
2. Else if Ollama is reachable at `LLM_BASE_URL` → use Ollama
3. Else → template-only mode (no network calls, docstrings still generated)

---

## 2. Local Development

### 2a. Backend

```bash
# From repository root
pip install -e .

uvicorn autodocstring.api.app:app --reload --port 8001 --app-dir src
```

Verify it is running:

```bash
curl http://localhost:8001/api/v1/health
```

Expected response:

```json
{
  "status": "healthy",
  "llm_available": true,
  "session_count": 0,
  "uptime_seconds": 4
}
```

If `llm_available` is `false`, no LLM key is set — generation still works via the template engine.

### 2b. Frontend

```bash
cd project/frontend
npm install
npm run dev
```

The app will be at `http://localhost:5173`.

The frontend reads `VITE_API_BASE` from `project/frontend/.env.development` (already configured for local dev — no changes needed):

```env
VITE_API_BASE=http://localhost:8001/api/v1
```

---

## 3. Verifying the Full Stack

1. Open `http://localhost:5173`
2. Upload one or more `.py` files from `demo/` (e.g. `01_clean_slate.py`)
3. Select a docstring style and click **Inspect**
4. Click **Generate Docstrings**
5. In the Review phase, check the navigator: 🟢 Generated · 🔵 Pre-existing · ⚪ Skipped
6. Click **Download Project** to get the documented ZIP

If a phase fails, check the browser console and the uvicorn terminal.

---

## 4. Cloud Deployment (Production)

The production deployment uses:

- **Backend → [Render](https://render.com)** (free tier, auto-deploy on `git push`)
- **Frontend → [Vercel](https://vercel.com)** (free tier, auto-deploy on `git push`)

### 4a. Backend — Render

1. Create a new **Web Service** on Render pointing to your GitHub repo
2. Set the **Build Command**:
   ```
   pip install -e .
   ```
3. Set the **Start Command**:
   ```
   uvicorn autodocstring.api.app:app --host 0.0.0.0 --port $PORT --app-dir src
   ```
4. Add the following **Environment Variables** in the Render dashboard:

   | Variable            | Value                                |
   | ------------------- | ------------------------------------ |
   | `GROQ_API_KEY`      | `gsk_...`                            |
   | `ALLOWED_ORIGINS`   | `https://your-vercel-app.vercel.app` |
   | `SESSION_DIR`       | `/tmp`                               |
   | `SESSION_TTL_HOURS` | `2`                                  |

   > **Important:** Set `SESSION_DIR=/tmp` on Render because the app directory is read-only. The path sandbox in `_resolve_safe_path` is aware of this and allows both `PROJECT_ROOT` and `SESSION_DIR` as valid roots.

5. Every `git push` to the connected branch triggers an automatic redeploy.

### 4b. Frontend — Vercel

1. Import your GitHub repo on Vercel
2. Set **Framework Preset** to `Vite`
3. Set **Root Directory** to `project/frontend`
4. Add the following **Environment Variable**:

   | Variable        | Value                                             |
   | --------------- | ------------------------------------------------- |
   | `VITE_API_BASE` | `https://your-render-backend.onrender.com/api/v1` |

5. Every `git push` triggers an automatic redeploy.

### 4c. Self-hosted (nginx)

```bash
# Build the frontend
cd project/frontend
npm run build
# Output: project/frontend/dist/

# Run backend (no --reload in production)
uvicorn autodocstring.api.app:app \
    --host 0.0.0.0 \
    --port 8001 \
    --workers 2 \
    --app-dir src
```

nginx configuration:

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

Set `ALLOWED_ORIGINS=https://yourdomain.com` to match your exact frontend domain.

---

## 5. GitHub Actions CI

The workflow at `.github/workflows/ci.yml` runs on every `push` and `pull_request`:

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

To reproduce locally:

```bash
pip install -e ".[dev]"
pytest --tb=short
```

---

## 6. Common Issues

| Problem                                      | Cause                                              | Fix                                                    |
| -------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------ |
| `uvicorn: command not found`                 | Package not installed                              | `pip install -e .` from repo root                      |
| `Module autodocstring not found`             | Wrong `--app-dir`                                  | Must pass `--app-dir src`                              |
| `CORS blocked in browser`                    | `ALLOWED_ORIGINS` mismatch                         | Set `ALLOWED_ORIGINS` to exact frontend origin         |
| `403 Access denied` on `/preview` or `/file` | `SESSION_DIR` outside `PROJECT_ROOT`               | Set `SESSION_DIR=/tmp` and redeploy backend            |
| Frontend shows "Cannot connect to backend"   | Backend not running or wrong `VITE_API_BASE`       | Verify backend URL in `.env.development`               |
| `npm install` fails                          | Old Node.js version                                | Upgrade to Node.js 18 LTS                              |
| `GROQ_API_KEY invalid`                       | Wrong key format                                   | Keys start with `gsk_`; copy from Groq console         |
| Render build fails                           | Read-only filesystem                               | Ensure `SESSION_DIR=/tmp` is set in Render env vars    |
| Sessions not cleaned up                      | `SESSION_TTL_HOURS` too high or no background task | Background task starts automatically on server startup |
