# Deployment Implementation Plan
**Project:** AutoDocString / DocGen  
**Date:** March 4, 2026  
**Source:** AUDIT_REPORT.md (baseline score: 71/100)  
**Target:** 90+ / 100 deployment readiness

---

## 1. Priority Map

### P0 — Deployment Blockers (fix first, nothing works without these)

| ID | Issue | Why P0 |
|---|---|---|
| P0-1 | `README.md` missing at root | `pip install -e .` crashes immediately on fresh clone — `pyproject.toml` has `readme = "README.md"`. Any CI, any reviewer, any deployment pipeline fails at install step. |
| P0-2 | API URL hardcoded to `http://localhost:8001/api/v1` | The frontend will always try to reach `localhost` — which does not exist on any server, Vercel, Render, or Docker network. Every API call fails silently. |
| P0-3 | No environment variable support in frontend | Without `import.meta.env.VITE_API_BASE`, the API URL cannot be injected at build time. Makes P0-2 unfixable without changing source code on every deploy. |

---

### P1 — Production Hardening (fix before going public)

| ID | Issue | Why P1 |
|---|---|---|
| P1-1 | CORS `allow_origins=["*"]` | Allows any website to call the API. Acceptable for internal tools but a real security risk for anything public-facing. Must be scoped to the known frontend domain. |
| P1-2 | Backend port hardcoded to `8001` | Cannot change port without editing source. Blocks Docker port mapping, PaaS configs, and load balancer setups. |
| P1-3 | LLM base URL hardcoded in `pyproject.toml` | Cannot point to a different Ollama/Gemini endpoint without editing config. Blocks multi-environment setups. |
| P1-4 | `.github/workflows/` is empty | CI/CD folder exists but does nothing. No automated test run on PR, no deployment gate. Dangerous for a shared repo. |
| P1-5 | `pyproject.toml` URLs point to old repo | Homepage, Repository, Issues all link to `Automated-Python-Docstring-Generator`. Breaks PyPI metadata and contributor navigation. |

---

### P2 — Repository Hygiene (fix before final submission)

| ID | Issue | Why P2 |
|---|---|---|
| P2-1 | Root `frontend/` dead scaffold | Confuses tooling (two `package.json` with same name), confuses contributors. No functional risk but creates noise. |
| P2-2 | Root `PROJECT_EXPLANATION.md` duplicate | Exact copy of `docs/PROJECT_EXPLANATION.md`. Two sources of truth diverge over time. |
| P2-3 | Root `TESTING_GUIDE.md` duplicate | Same as P2-2. |
| P2-4 | `project/backend/` empty folder | Zero code, one README. Implies backend lives here — it does not. Misleads every new developer. |
| P2-5 | `tsconfig.app.json` has `/* */` comments | JSON strict mode warning in VS Code. Cosmetic but visible in editor. |

---

### P3 — Optional Improvements (nice to have)

| ID | Issue | Why P3 |
|---|---|---|
| P3-1 | No `@/` path aliases in `tsconfig.app.json` | All imports use relative paths. Works fine, just less clean as the project grows. |
| P3-2 | No explicit `build.outDir` in `vite.config.ts` | Defaults to `dist/`. Fine for now, but explicit config avoids surprises with Docker COPY paths. |
| P3-3 | No Vite dev server proxy | Dev relies on CORS. A proxy is cleaner but not strictly necessary if CORS is correctly set. |

---

## 2. Minimal Deployment Change Set

This is the **smallest possible set of changes** to go from broken → deployable. No architecture redesign. No refactor.

### Change 1 — Create `README.md` at root
- **File:** `README.md` (new)
- **Content needed:** Minimum: project name, install command, run command.
- **Fixes:** P0-1
- **Risk:** Zero

### Change 2 — Add env var support to frontend
- **File:** `project/frontend/src/apiClient.ts` line 1
- **Change:** Replace `'http://localhost:8001/api/v1'` with `import.meta.env.VITE_API_BASE ?? 'http://localhost:8001/api/v1'`
- **Fixes:** P0-2, P0-3
- **Risk:** Zero — falls back to `localhost` in local dev

### Change 3 — Add `.env` files for frontend
- **Files:** `project/frontend/.env.development` and `project/frontend/.env.production`
- **Development:** `VITE_API_BASE=http://localhost:8001/api/v1`
- **Production:** `VITE_API_BASE=` ← filled at deploy time (Vercel env var, Docker ARG, etc.)
- **Fixes:** P0-3
- **Risk:** Zero — `.env` files don't affect anything unless explicitly used

### Change 4 — Add `PORT` env var support to backend
- **File:** `src/autodocstring/api/app.py` (startup / uvicorn call)
- **Change:** Read `PORT = int(os.getenv("PORT", "8001"))`
- **Fixes:** P1-2
- **Risk:** Very low — defaults to 8001 unchanged

### Change 5 — Restrict CORS origins via env var
- **File:** `src/autodocstring/api/app.py` line 143
- **Change:** `allow_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")`
- **Fixes:** P1-1
- **Risk:** Low — defaults to `*`, preserving current behavior until explicitly set

### Change 6 — Update `pyproject.toml` URLs
- **File:** `pyproject.toml`
- **Change:** Replace all 3 URLs from `Automated-Python-Docstring-Generator` → `DocGen`
- **Fixes:** P1-5
- **Risk:** Zero

### Change 7 — Safe file cleanup
- Delete `frontend/` root scaffold
- Delete root `PROJECT_EXPLANATION.md`
- Delete root `TESTING_GUIDE.md`
- Delete `project/backend/` empty folder
- **Fixes:** P2-1 through P2-4
- **Risk:** Zero — none of these files are imported or used anywhere

### Change 8 — Add minimal CI workflow
- **File:** `.github/workflows/ci.yml` (new)
- **Content:** Install Python deps → run `pytest` → done
- **Fixes:** P1-4
- **Risk:** Zero

---

## 3. Environment Variable Architecture

### Backend Environment Variables

| Variable | Default (local dev) | Production override | Source in code |
|---|---|---|---|
| `PORT` | `8001` | Set by PaaS / Docker | `int(os.getenv("PORT", "8001"))` |
| `ALLOWED_ORIGINS` | `*` | `https://your-frontend.com` | `os.getenv("ALLOWED_ORIGINS", "*").split(",")` |
| `LLM_BASE_URL` | `http://localhost:11434` | Ollama server URL | `os.getenv("LLM_BASE_URL", "http://localhost:11434")` |
| `LLM_MODEL` | `mistral` | Any Ollama-compatible model | `os.getenv("LLM_MODEL", "mistral")` |

**Backend `.env` file (local dev only, never commit):**
```
PORT=8001
ALLOWED_ORIGINS=http://localhost:5173
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=mistral
```

---

### Frontend Environment Variables

| Variable | Default (dev) | Production value |
|---|---|---|
| `VITE_API_BASE` | `http://localhost:8001/api/v1` | `https://your-backend.com/api/v1` or `/api/v1` (if proxied via Nginx) |

**`project/frontend/.env.development`:**
```
VITE_API_BASE=http://localhost:8001/api/v1
```

**`project/frontend/.env.production`:**
```
VITE_API_BASE=https://your-backend-domain.com/api/v1
```

---

### How values flow in each deploy model

**Docker Compose:**
```
docker-compose.yml
  environment:
    - PORT=8001
    - ALLOWED_ORIGINS=http://localhost
    - LLM_BASE_URL=http://ollama:11434
```
Frontend built with `--build-arg VITE_API_BASE=/api` at Docker build time (Vite bakes it in at build).

**PaaS (Render + Vercel):**
- Backend: Set env vars in Render dashboard under "Environment"
- Frontend: Set `VITE_API_BASE` in Vercel dashboard under "Environment Variables" → Production

**Local dev:**
- Read from `.env.development` automatically by Vite
- Backend reads from shell or `.env` file loaded manually

---

## 4. Deployment Strategy Comparison

| Factor | Docker Compose | Split PaaS (Render + Vercel) | Single VPS | Railway |
|---|---|---|---|---|
| **Complexity** | Medium — need Dockerfile + compose | Low — UI-driven, no Docker needed | High — manual Nginx, SSL, OS config | Low — git-push deploy |
| **Cost** | Self-hosted (free if you have a server) | Free tier available both platforms | ~$5–10/month VPS | Free tier, then $5/month |
| **Maintainability** | High — reproducible, version-controlled | High — managed infra, auto-deploys | Low — manual updates, single point of failure | High — simple, git-native |
| **Scalability** | Medium — vertical only without Swarm/K8s | High — both scale independently | Low — tied to one machine | Medium — limited by plan |
| **Session state issue** | ✅ Works — shared volume possible | ⚠️ Risk — Render resets disk on redeploy | ✅ Works — persistent disk | ⚠️ Risk — ephemeral filesystem |
| **Setup time** | ~2–3 hours | ~1 hour | ~4–6 hours | ~30 minutes |
| **Best for** | Internal tools, demo, portfolio | Public-facing production | Advanced users with full control | Quick demo / prototype |

---

### Key constraint for this project

The backend uses **file-system session state** (temp directories per session). This means:
- Serverless → ❌ completely incompatible
- Render free tier → ⚠️ risky (ephemeral disk, sessions lost on redeploy)
- Railway → ⚠️ same risk on free tier
- Docker Compose / VPS → ✅ persistent disk, sessions survive restarts

---

### Final Recommendation

**Docker Compose on a VPS or local server** for demos and internship submission.  
**Reason:**
1. Sessions rely on temp disk — Docker volume solves this cleanly
2. Both services run together, easy to demo
3. Single `docker-compose up` command for anyone cloning the repo
4. No external service accounts needed
5. Nginx can serve the built React `dist/` and proxy `/api` to FastAPI — clean single-domain setup

For a lightweight public URL, deploy the Docker Compose stack to a **$5/month DigitalOcean Droplet or Fly.io machine** (not ephemeral).

---

## 5. Risk Simulation — Deploy Right Now Without Fixes

### Scenario A: Clone repo and run `pip install -e .`

```
ERROR: Error reading 'README.md': [Errno 2] No such file or directory
```
**Result:** Install fails. Backend cannot be installed. Nothing runs.  
**Cause:** P0-1 — `README.md` missing.

---

### Scenario B: Backend starts, frontend built and opened in browser

```
GET http://localhost:8001/api/v1/upload → net::ERR_CONNECTION_REFUSED
```
**Result:** Every API call fails with network error.  
**Cause:** P0-2 — API URL hardcoded to `localhost:8001`. On any real deployment the backend is not on `localhost` relative to the browser.

---

### Scenario C: Both deployed on same server, frontend calls backend

```
Access to fetch at 'http://localhost:8001/...' from origin 'https://your-domain.com' 
has been blocked by CORS policy
```
**Result:** Browser blocks all API calls.  
**Cause:** Even with `allow_origins=["*"]`, browser blocks cross-origin requests when the URL itself is `localhost` from a public domain.

---

### Scenario D: GitHub Actions triggered on push

```
(nothing happens)
```
**Result:** No tests run, no deployment triggered, no status check on PR.  
**Cause:** P1-4 — `.github/workflows/` folder is empty.

---

### Scenario E: Someone runs `npm install && npm run dev` from root `frontend/`

```
vite: error when starting dev server
Cannot find module './App' or its corresponding type declarations
```
**Result:** Dev server crashes.  
**Cause:** P2-1 — root `frontend/` scaffold has `main.tsx` importing `App` which doesn't exist there.

---

### Scenario F: PyPI metadata published or pip show run

```
Homepage: https://github.com/Megesh07/Automated-Python-Docstring-Generator (404)
```
**Result:** Links to non-existent or wrong repo.  
**Cause:** P1-5 — `pyproject.toml` URLs not updated after repo rename to `DocGen`.

---

## 6. Projected Score After Fixes

| Phase | Fixes Applied | Estimated Score |
|---|---|---|
| Current | None | 71 / 100 |
| After P0 | README + env vars + API URL | 82 / 100 |
| After P0 + P1 | CORS + PORT + CI + URLs | 90 / 100 |
| After P0 + P1 + P2 | Cleanup duplicates + dead scaffold | 95 / 100 |
| After all | P3 aliases + proxy + outDir | 98 / 100 |

**Minimum to hit 90:** Complete all P0 and P1 items only (8 targeted changes).
