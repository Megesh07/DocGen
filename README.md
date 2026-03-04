# DocGen — Automated Python Docstring Generator

> Upload Python files → inspect coverage → generate docstrings with AI → download documented project.

**Live demo:** [https://doc-gen-fo6v.vercel.app](https://doc-gen-fo6v.vercel.app)  
**Backend API (Render):** [https://docgen-backend-hryu.onrender.com](https://docgen-backend-hryu.onrender.com)

---

## Features

| Feature                    | Detail                                                                                                                                           |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Upload-based workflow**  | Drag-and-drop `.py` files; no local paths exposed to the server                                                                                  |
| **5 docstring styles**     | Google · NumPy · reST · Epytext · Sphinx                                                                                                         |
| **AI-enhanced summaries**  | Groq (`llama-3.3-70b-versatile`) generates the one-sentence summary; all sections (Args/Returns/Raises) are template-rendered — no hallucination |
| **Template-only fallback** | Works 100 % offline without a Groq API key                                                                                                       |
| **Coverage inspection**    | Per-file and per-function coverage stats before you generate                                                                                     |
| **Function Navigator**     | Left-panel navigator with 🟢 Generated / 🔵 Pre-existing / ⚪ Skipped colour-coding                                                              |
| **Side-by-side diff**      | Original vs Documented viewer with highlighted new docstring ranges                                                                              |
| **Download as ZIP**        | One-click download of all documented files                                                                                                       |
| **Error resilience**       | On failure, user stays on the Inspect page and can retry without re-uploading                                                                    |
| **Session safety**         | UUID sessions, auto-cleanup after 2 h, syntax-validation before any write                                                                        |

---

## Workflow

```
1. Upload    → drag-and-drop .py files + choose docstring style
2. Inspect   → static analysis report: coverage %, missing params/returns
3. Generate  → AI + template engine writes docstrings (activity log shown live)
4. Review    → side-by-side diff + navigator + coverage improvement summary
              → Download ZIP
```

---

## Quick Start (Local)

### Backend

```bash
# From repository root
pip install -e .

uvicorn autodocstring.api.app:app --reload --port 8001 --app-dir src
```

API: `http://localhost:8001`  
Swagger UI: `http://localhost:8001/docs`

### Frontend

```bash
cd project/frontend
npm install
npm run dev
```

UI: `http://localhost:5173`

> The frontend reads `VITE_API_BASE` from `project/frontend/.env.development` — no changes needed for local development.

---

## Environment Variables

Place in a `.env` file at the repository root (gitignored):

```env
# LLM — optional; app works offline without this
GROQ_API_KEY=gsk_...

# Backend overrides (all optional)
ALLOWED_ORIGINS=http://localhost:5173   # comma-separated CORS origins
SESSION_DIR=.autodocstring_sessions     # session storage directory
SESSION_TTL_HOURS=2                     # auto-cleanup TTL
LLM_MODEL=llama-3.3-70b-versatile
LLM_TIMEOUT=45
```

---

## API Endpoints

| Method | Path                            | Purpose                                                             |
| ------ | ------------------------------- | ------------------------------------------------------------------- |
| GET    | `/api/v1/health`                | Health check — LLM availability, session count, uptime              |
| POST   | `/api/v1/upload`                | Upload `.py` files (multipart), create session, return scan results |
| POST   | `/api/v1/rescan`                | Re-scan session files with a new docstring style                    |
| GET    | `/api/v1/file`                  | Fetch original source of a session file                             |
| POST   | `/api/v1/preview`               | Get full-file preview with docstrings injected (no disk write)      |
| POST   | `/api/v1/generate`              | Generate docstrings for a specific function                         |
| POST   | `/api/v1/generate/file`         | Generate docstrings for all functions in one file                   |
| POST   | `/api/v1/generate/all`          | Generate docstrings for all files in the session                    |
| POST   | `/api/v1/generate/cancel`       | Cancel an in-progress bulk generation                               |
| POST   | `/api/v1/save_file`             | Persist user-edited file content to session                         |
| GET    | `/api/v1/download/{session_id}` | Download documented files as a ZIP                                  |
| GET    | `/api/v1/coverage`              | Session coverage statistics                                         |

---

## Tests

```bash
pip install -e ".[dev]"
pytest
pytest --cov=src/autodocstring --cov-report=term-missing
```

See [`docs/TESTING.md`](docs/TESTING.md) for the full test guide.

---

## Documentation

| File                                           | Contents                                                        |
| ---------------------------------------------- | --------------------------------------------------------------- |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Full system design: backend modules, frontend phases, data flow |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)     | Local setup, Render + Vercel cloud deployment, CI               |
| [`docs/SECURITY.md`](docs/SECURITY.md)         | Secrets management, CORS, path sandbox, session isolation       |
| [`docs/TESTING.md`](docs/TESTING.md)           | Test suite structure and how to run it                          |

---

## Demo Files

The `demo/` directory contains 4 Python files that cover every generation scenario:

| File                      | Scenario                                                                             |
| ------------------------- | ------------------------------------------------------------------------------------ |
| `01_clean_slate.py`       | Fully typed, zero docstrings → 100 % AUTO_APPLY                                      |
| `02_mixed_state.py`       | Pre-existing docs preserved · `# autodoc: ignore` respected · undocumented generated |
| `03_confidence_stress.py` | Missing types, high branches, generators → REVIEW / SKIP zones                       |
| `04_edge_cases.py`        | @dataclass, @property, ABC, async generator, closures, Union/Optional                |

---

## Tech Stack

| Layer      | Technology                                       |
| ---------- | ------------------------------------------------ |
| Backend    | Python 3.11 · FastAPI · Uvicorn · Pydantic v2    |
| LLM        | Groq API · llama-3.3-70b-versatile (optional)    |
| Frontend   | React 18 · TypeScript · Vite 5 · Zustand         |
| Styling    | Vanilla CSS with CSS variables (dark-mode ready) |
| Deployment | Backend → Render · Frontend → Vercel             |
| CI         | GitHub Actions (`pytest` on every push)          |
