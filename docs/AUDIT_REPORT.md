# Technical Intelligence Audit Report
**Project:** AutoDocString / DocGen  
**Date:** March 4, 2026  
**Repo:** https://github.com/Megesh07/DocGen

---

## 1. Folder Structure Summary

```
root/  (Automated-Python-Docstring-Generator-main)
├── .github/workflows/          ⚠️  EXISTS but EMPTY (no .yml files)
├── .gitignore                  ✅
├── .pre-commit-hooks.yaml      ✅
├── LICENSE                     ✅
├── pyproject.toml              ✅ (single, root level)
├── setup.py                    ✅
├── README.md                   ❌ MISSING (referenced in pyproject.toml)
├── PROJECT_EXPLANATION.md      ❌ DUPLICATE of docs/
├── TESTING_GUIDE.md            ❌ DUPLICATE of docs/
│
├── src/autodocstring/          ✅ REAL BACKEND
│   ├── api/app.py              ← main FastAPI app (1172 lines)
│   ├── api/schemas.py
│   ├── confidence/scorer.py
│   ├── config/loader.py
│   ├── core/decision_model.py
│   ├── generator/ (engine, gemini_provider, ollama_provider, templates/)
│   ├── integrations/precommit.py
│   ├── models/metadata.py
│   ├── parser/ (ast_parser, extractors)
│   ├── safety/ (applier, git_diff, transaction)
│   ├── session/session_manager.py
│   ├── utils/files.py
│   └── validation/ (coverage, rules, style_checker, validator)
│
├── project/
│   ├── backend/README.md       ⚠️  EMPTY FOLDER (no code)
│   └── frontend/               ✅ REAL FRONTEND
│       ├── index.html
│       ├── vite.config.ts
│       ├── package.json
│       ├── package-lock.json
│       ├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
│       ├── eslint.config.js
│       └── src/
│           ├── main.tsx        ← entry point
│           ├── App.tsx
│           ├── apiClient.ts
│           ├── App.css / index.css
│           ├── components/ (11 .tsx files)
│           └── store/sessionStore.ts
│
├── frontend/                   ❌ DEAD SCAFFOLD (no index.html, no App.tsx)
│   └── src/ (only App.css, index.css, main.tsx — broken)
│
├── demo/                       ✅ (5 demo categories)
├── docs/                       ✅ (PROJECT_EXPLANATION + TESTING_GUIDE)
└── tests/                      ✅ (6 test files + fixtures + sample_project)
```

### Multiple `package.json` Files

| Path | Name | Status |
|---|---|---|
| `project/frontend/package.json` | `autodocstring-frontend` | ✅ Real frontend |
| `frontend/package.json` | `autodocstring-frontend` | ❌ Dead scaffold, same name |

### Multiple `pyproject.toml` Files

Only 1 — at root. ✅

---

## 2. Backend Summary

| Property | Value |
|---|---|
| **Framework** | FastAPI |
| **Main entry** | `src/autodocstring/api/app.py` |
| **App object** | `app = FastAPI(title="AutoDocstring API", version="1.0", lifespan=lifespan)` |
| **Uvicorn command** | `python -m uvicorn autodocstring.api.app:app --reload --port 8001 --app-dir src` |
| **CORS** | `allow_origins=["*"]`, `allow_methods=["*"]` — **fully open, wildcard** |
| **Environment variables** | **NONE** — zero `os.environ` / `os.getenv` calls in entire backend |
| **LLM config** | Hardcoded in `pyproject.toml` (`llm_base_url = "http://localhost:11434"`) |
| **Port** | Hardcoded `8001` (no env var) |
| **Lifespan** | Uses `@asynccontextmanager lifespan` — correct modern FastAPI pattern |
| **Swagger UI** | Available at `http://localhost:8001/docs` |
| **Production-ready?** | ⚠️ NO — wildcard CORS, no env vars, no secrets management |

---

## 3. Frontend Summary

| Property | Value |
|---|---|
| **Framework** | React 19 + Vite 6 + TypeScript 5.6 + TailwindCSS 4 + Zustand 5 |
| **Real root** | `project/frontend/` |
| **`index.html`** | `project/frontend/index.html` ✅ |
| **Entry point** | `project/frontend/src/main.tsx` ✅ |
| **API base URL** | `const API_BASE = 'http://localhost:8001/api/v1'` — **hardcoded, no env var** |
| **Environment variable support** | ❌ None — no `import.meta.env.VITE_*` anywhere |
| **Build command** | `tsc -b && vite build` |
| **Output directory** | Default `dist/` (not explicitly set in `vite.config.ts`) |
| **Proxy config in Vite** | ❌ None — relies entirely on CORS |
| **Path aliases (`@/`)** | ❌ None in `tsconfig.app.json` |
| **`tsconfig.app.json` comments** | ⚠️ Has `/* ... */` comments — JSON-vs-JSONC issue |
| **Dead scaffold frontend** | `frontend/` root (no `index.html`, no components, cannot build) |

---

## 4. Architecture Type

**Monorepo — Decoupled Frontend + Backend**

- Backend: Python package (`src/autodocstring`)
- Frontend: React SPA (`project/frontend`)
- Communication: REST over HTTP (fetch API, no WebSockets, no shared state)
- They are **loosely coupled** by contract (API endpoints) but **tightly coupled by URL** (`localhost:8001` hardcoded)

---

## 5. Deployment Options (Ranked)

| Rank | Strategy | Notes |
|---|---|---|
| 1 | **Local dev** (current) | Both services run manually. Works today. |
| 2 | **Docker Compose** | Best fit — separate containers for FastAPI + Nginx serving React `dist/`. Not yet configured. |
| 3 | **PaaS split** | Backend → Railway / Render / Fly.io. Frontend → Vercel / Netlify. Requires env var for API URL. |
| 4 | **Static hosting only** | ❌ Not possible — backend is required for all functionality. |
| 5 | **Serverless** | ❌ Not compatible — session state is file-system based (temp dirs). |

---

## 6. Blockers

### 🔴 Critical (must fix before deploy)

| # | Blocker | Impact |
|---|---|---|
| B1 | `README.md` missing at root | `pip install -e .` fails on fresh clone — `pyproject.toml` references it |
| B2 | API URL hardcoded to `localhost:8001` | Frontend cannot contact backend in any deployed environment |
| B3 | No env var support anywhere | Cannot configure backend port, LLM URL, or API base without code edits |
| B4 | CORS `allow_origins=["*"]` | Any website can call the API — security risk in shared/public deployment |
| B5 | `.github/workflows/` is empty | CI/CD folder exists but has no YAML files — no automation on push |

### 🟡 Medium (recommended fixes)

| # | Issue |
|---|---|
| M1 | `project/backend/` folder — empty, misleads contributors |
| M2 | `pyproject.toml` URLs still reference old repo `Automated-Python-Docstring-Generator` not `DocGen` |
| M3 | Root `frontend/` dead scaffold — same `package.json` name as real frontend, confuses tooling |
| M4 | Root `PROJECT_EXPLANATION.md` and `TESTING_GUIDE.md` are exact duplicates of `docs/` versions |
| M5 | No `vite.config.ts` `base` or `build.outDir` — default `dist/` assumed, may break deployment |
| M6 | `tsconfig.app.json` has `/* ... */` comments — JSON-vs-JSONC issue |

### 🟢 Safe Cleanup (no risk)

| Item |
|---|
| Delete `frontend/` root dead scaffold |
| Delete root `PROJECT_EXPLANATION.md` |
| Delete root `TESTING_GUIDE.md` |
| Delete `project/backend/` (empty folder) |

---

## 7. Recommended Deployment Strategy

**Target: Docker Compose (best fit given architecture)**

```
[Browser]
    ↓ :80
[Nginx container]  ← serves React dist/
    ↓ /api → proxy to :8001
[FastAPI container]  ← uvicorn autodocstring.api.app:app
```

### What needs to change for this to work

1. Create `README.md` at root
2. Replace hardcoded `http://localhost:8001` in `apiClient.ts` with `import.meta.env.VITE_API_BASE`
3. Add `VITE_API_BASE=/api` to `.env.production`
4. Add Nginx proxy block `/api → http://backend:8001`
5. Add `Dockerfile` for backend
6. Add `docker-compose.yml`
7. Tighten `allow_origins` to specific domain
8. Update `pyproject.toml` URLs to `DocGen` repo
9. Add CI/CD workflow YAML to `.github/workflows/`

---

## Deployment Readiness Score

```
Backend (Python/FastAPI)    ████████░░  78/100
Frontend (React/Vite)       ██████░░░░  62/100
Git / Repo hygiene          ████████░░  75/100
Documentation               ███████░░░  68/100
─────────────────────────────────────────────
Overall Score               71 / 100
```

**Blockers keeping this below 90:**
- Missing root `README.md` (`pip install` breaks)
- Hardcoded `localhost:8001` in frontend
- Dead `frontend/` scaffold folder adds confusion
- No CI/CD pipeline configured
