# Architecture — DocGen (Automated Python Docstring Generator)

## 1. Overview

DocGen is a full-stack web application that automatically generates, reviews, and applies Python docstrings. It follows a clean three-tier architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (React/TypeScript)                │
│          Vercel · https://doc-gen-fo6v.vercel.app            │
└────────────────────────┬────────────────────────────────────┘
                         │  REST (JSON over HTTPS)
┌────────────────────────▼────────────────────────────────────┐
│               FastAPI Backend (Python 3.11+)                 │
│     Render · https://docgen-backend-hryu.onrender.com        │
└────────────────────────┬────────────────────────────────────┘
                         │  HTTPS (optional)
┌────────────────────────▼────────────────────────────────────┐
│              Groq Cloud LLM API (optional)                   │
│          llama-3.3-70b-versatile  (summary only)             │
└─────────────────────────────────────────────────────────────┘
```

The backend is stateless per-request. Session state is persisted to disk under `SESSION_DIR` (default: `.autodocstring_sessions/<uuid>/`) so the browser can resume across page refreshes. Sessions auto-expire after `SESSION_TTL_HOURS` (default: 2 h).

---

## 2. Repository Structure

```
DocGen/
├── src/
│   └── autodocstring/          # Backend Python package
│       ├── api/                # FastAPI routes + Pydantic schemas
│       │   ├── app.py          # All route handlers (~1200 lines)
│       │   └── schemas.py      # Pydantic v2 request/response models
│       ├── parser/             # AST-based Python source analysis
│       ├── generator/          # Docstring generation engines + templates
│       │   ├── engine.py       # HybridDocstringEngine orchestrator
│       │   ├── generator.py    # DocstringGenerator (deterministic)
│       │   ├── groq_provider.py
│       │   ├── gemini_provider.py
│       │   ├── ollama_provider.py
│       │   └── templates/      # GoogleTemplate, NumpyTemplate, RestTemplate …
│       ├── confidence/         # Risk scoring (offline, deterministic)
│       ├── safety/             # Safe file writer with AST rollback
│       ├── validation/         # Style checker + completeness checker
│       ├── session/            # Session lifecycle management
│       ├── models/             # Shared dataclasses (FunctionMetadata, DocstringResult)
│       ├── integrations/       # Pre-commit hook helper
│       └── utils/              # Shared helpers
│
├── project/
│   └── frontend/               # React/TypeScript SPA
│       ├── src/
│       │   ├── App.tsx
│       │   ├── main.tsx
│       │   ├── apiClient.ts    # Typed fetch wrapper for all API calls
│       │   ├── components/
│       │   │   ├── WorkflowPage.tsx    # Phase orchestrator
│       │   │   ├── PhaseHeader.tsx     # Breadcrumb nav (Upload→Inspect→Generate→Review)
│       │   │   ├── UploadPhase.tsx     # Drag-and-drop file upload + style picker
│       │   │   ├── UploadZone.tsx
│       │   │   ├── AnalyzePhase.tsx    # Inspect: coverage report + Generate button
│       │   │   ├── GeneratePhase.tsx   # Animated activity log during generation
│       │   │   ├── ReviewPhase.tsx     # Side-by-side diff + navigator + download
│       │   │   ├── FunctionNavigator.tsx
│       │   │   ├── ComparisonViewer.tsx
│       │   │   ├── CoverageReport.tsx
│       │   │   └── ImprovementBanner.tsx
│       │   └── store/
│       │       └── sessionStore.ts     # Zustand global state
│       ├── index.html
│       ├── package.json
│       └── vite.config.ts
│
├── tests/                      # pytest test suite
├── demo/                       # 4 demo Python files covering every edge case
│   ├── 01_clean_slate.py
│   ├── 02_mixed_state.py
│   ├── 03_confidence_stress.py
│   ├── 04_edge_cases.py
│   └── README.md
├── docs/                       # Project documentation
├── .github/workflows/ci.yml    # GitHub Actions CI
├── pyproject.toml
└── README.md
```

---

## 3. Backend Architecture

### 3.1 API Layer — `src/autodocstring/api/app.py`

All endpoints are registered under the `/api/v1` prefix:

| Method | Path                            | Purpose                                                               |
| ------ | ------------------------------- | --------------------------------------------------------------------- |
| GET    | `/api/v1/health`                | Health check — LLM status, session count, uptime                      |
| POST   | `/api/v1/upload`                | Upload `.py` files (multipart/form-data), create session, return scan |
| POST   | `/api/v1/rescan`                | Re-scan session files with a different docstring style                |
| GET    | `/api/v1/file`                  | Return raw source of a session file                                   |
| POST   | `/api/v1/preview`               | Return full-file source with docstrings injected (no disk write)      |
| POST   | `/api/v1/generate`              | Generate docstrings for one specific function                         |
| POST   | `/api/v1/generate/file`         | Generate docstrings for all functions in one file                     |
| POST   | `/api/v1/generate/all`          | Generate docstrings for all files in the session                      |
| POST   | `/api/v1/generate/cancel`       | Cancel an in-progress bulk generation                                 |
| POST   | `/api/v1/save_file`             | Persist user-edited content to session workspace                      |
| GET    | `/api/v1/coverage`              | Session coverage statistics                                           |
| GET    | `/api/v1/download/{session_id}` | Download documented files as a `zip`                                  |

**Key helpers in `app.py`:**

- `_docstring_status(docstring, metadata, style)` — determines whether an existing docstring is "complete and correct style" or needs regeneration. A docstring is valid only when BOTH `is_style_match` AND `is_complete` return `True`.
- `_build_signature(func)` — builds a human-readable function signature (`add(a: int, b: int) -> int`) returned to the frontend so the Inspect phase can display which params/returns are missing without deserialising full metadata.
- `_resolve_safe_path(raw_path)` — path sandbox: resolves the given path and verifies it is located under either `PROJECT_ROOT` **or** `_SESSIONS_ROOT`. Raises `HTTP 403` if outside both roots. This covers session workspace files that may live in a separate directory (e.g. `/tmp` on Render if `SESSION_DIR=/tmp`).

**Upload flow:**

When files are uploaded via `POST /upload`, the backend:

1. Creates a UUID session in `SessionManager`
2. Saves each `.py` file to `_SESSIONS_DIR/<session_id>/workspace/`
3. Runs AST parsing + `ConfidenceScorer` on each file
4. Returns `ScanResponse` with `session_id`, full file paths on the server, and per-function metadata

The frontend stores these absolute server-side paths and sends them back in subsequent `preview` and `file` requests. The sandbox check in `_resolve_safe_path` allows paths under `_SESSIONS_DIR` for exactly this reason.

### 3.2 Parser — `src/autodocstring/parser/`

**`ast_parser.py`** — Walks the Python AST and returns a `ModuleMetadata` object:

- Module-level docstring
- Top-level `FunctionMetadata` objects
- `ClassMetadata` objects, each containing `FunctionMetadata` for methods

**`extractors.py`** — Extracts per-function:

- Parameter names, type hints, default values
- Return type annotation
- Decorators (`@staticmethod`, `@classmethod`, `@property`)
- Whether the function is `async def`
- `# autodoc: ignore` directive

### 3.3 Generator — `src/autodocstring/generator/`

Two engines are provided:

#### `DocstringGenerator` (deterministic, pure template)

- Instantiated with a style (`google`, `numpy`, `rest`, `epytext`, `sphinx`)
- Selects the matching `BaseTemplate` subclass from `generator/templates/`
- Renders: one-sentence summary placeholder → Args section → Returns section → Raises section
- No network calls; always produces output

#### `HybridDocstringEngine` (production engine)

Full pipeline per function:

```
FunctionMetadata
       │
       ▼
[1] # autodoc: ignore directive?  ──YES──► skip (generation_type="skipped")
       │ NO
       ▼
[2] docstring already present & rewrite_existing=False?  ──YES──► keep existing
       │ NO
       ▼
[3] ConfidenceScorer.score(metadata)
       ├─ confidence < 0.60 ──► skip
       ▼
[4] DocstringGenerator.generate_function_docstring(metadata)
       │   (deterministic template render)
       ▼
[5] LLM provider available?
       ├─ YES → send only func_signature to Groq
       │         receive one-sentence summary → replace template placeholder
       │         generation_type = "llm_enhanced"
       └─ NO  → keep template summary
               generation_type = "template"
       ▼
[6] DocstringValidator.fix_docstring()  (auto-fix: spacing, trailing period)
       ▼
DocstringResult(docstring, confidence, risk, generation_type, reason)
```

**LLM Providers:**

- `groq_provider.py` — `llama-3.3-70b-versatile` via Groq OpenAI-compatible endpoint; 45 s timeout; falls back gracefully on any error
- `gemini_provider.py` — Google Gemini (requires `GEMINI_API_KEY`)
- `ollama_provider.py` — Local Ollama instance (`LLM_BASE_URL` env var)

When `GROQ_API_KEY` is set, GroqProvider is selected automatically. When absent, OllamaProvider is tried. The frontend can also explicitly select `gemini` as the provider.

**Only the function signature is sent to the LLM** — the function body, comments, and variable names are never transmitted.

**Templates** (`generator/templates/`):
Each template inherits from `BaseTemplate` and implements:

- `generate_function_docstring(metadata)` → full formatted docstring
- `generate_class_docstring(metadata)` → class docstring

### 3.4 Confidence Scorer — `src/autodocstring/confidence/scorer.py`

Stateless, offline, purely deterministic. Starts at `confidence = 1.0` and applies penalties:

| Condition                                      | Penalty |
| ---------------------------------------------- | ------- |
| Each parameter without a type hint             | −0.05   |
| No return type annotation                      | −0.10   |
| AST branch count > 8 (if/for/while/try/BoolOp) | −0.10   |
| Generator function (`yield`)                   | −0.05   |
| External call to non-whitelisted module        | −0.05   |

**Decision thresholds:**

- `confidence ≥ 0.85` → `AUTO_APPLY`
- `0.60 ≤ confidence < 0.85` → `REVIEW`
- `confidence < 0.60` → skip

### 3.5 Safety Applier — `src/autodocstring/safety/applier.py`

`_insert_docstrings()` injects docstrings into source files with safety guarantees:

1. **Syntax safety** — after generation, `ast.parse()` is called; on `SyntaxError` the original is restored
2. **Non-intrusive** — only docstring statement nodes are modified; formatting, imports, comments untouched
3. **Idempotency** — if a docstring already matches, the file is not modified
4. **Dry-run / preview** — can return source-with-docstrings as a string without writing to disk (used by `/preview`)

Handles `ast.FunctionDef`, `ast.AsyncFunctionDef`, and `ast.ClassDef`.

### 3.6 Session Manager — `src/autodocstring/session/session_manager.py`

Each workflow run gets a UUID session. The `SessionManager` stores:

- In-memory `ReviewSession` dataclasses (thread-safe with `threading.RLock`)
- On-disk JSON files at `_SESSIONS_DIR/session_<id>.json` (atomic temp→rename writes)
- Uploaded files at `_SESSIONS_DIR/<session_id>/workspace/<filename>`
- Batch snapshots at `_SESSIONS_DIR/<batch_id>/<hash>_<filename>` (for undo/cancel)

**Key fields on `ReviewSession`:**

- `session_id` — UUID v4
- `scan_results` — list of `DocstringResultSchema` dicts (updated after every generate call)
- `file_hashes` — SHA256 per file for conflict detection
- `docstring_style` — persisted style selection
- `current_batch_id` — UUID of the active generation batch (for cancel/undo)
- `is_cancelled` — flag checked by the generation engine per-file

**`SESSION_DIR`** can be overridden by environment variable (e.g. `SESSION_DIR=/tmp` on Render). The path sandbox in `_resolve_safe_path` automatically tracks this resolved directory so that preview/file calls work correctly regardless of where sessions are stored.

Background cleanup task runs every 30 minutes to purge expired sessions and orphaned batch snapshots.

### 3.7 Validation — `src/autodocstring/validation/`

**`style_checker.py`:**

- `is_style_match(docstring, style, metadata)` — detects format (Google `Args:`, NumPy dashed headers, reST `:param:`, etc.) and checks against requested style
- `is_complete(docstring, metadata)` — verifies all non-self/cls parameters are documented and Returns is present when a return annotation exists

**`validator.py`** — post-generation `DocstringValidator`:

- Runs after every AI/template generation
- `validate_docstring()` — returns structured issues (errors, warnings)
- `fix_docstring()` — auto-fixes cosmetic issues (missing trailing period, extra blank lines)
- `autofix=True` is always enabled in production; `use_pydocstyle=False` (avoids heavyweight dependency in production)

---

## 4. Frontend Architecture

### 4.1 Technology Stack

| Layer            | Technology                                                                      |
| ---------------- | ------------------------------------------------------------------------------- |
| Framework        | React 18 + TypeScript                                                           |
| Build tool       | Vite 5                                                                          |
| State management | Zustand (`sessionStore.ts`)                                                     |
| HTTP client      | `apiClient.ts` (typed fetch wrapper)                                            |
| Styling          | Inline styles + CSS variables (`--bg-page`, `--text-primary`, `--border`, etc.) |
| Linting          | ESLint 9 (flat config)                                                          |
| Deployment       | Vercel (auto-deploy on `git push`)                                              |

### 4.2 Workflow Phase Model

The UI is a **4-phase linear wizard** controlled by the `phase` field in `sessionStore`:

```
idle → analyzing → analyzed → generating → done
  ↑          ↑          ↑           ↑          ↑
Upload    uploading  Inspect    Generate    Review
```

Each phase maps to one of these rendered components:

| Phase value          | Rendered component           | User sees                                                           |
| -------------------- | ---------------------------- | ------------------------------------------------------------------- |
| `idle` / `analyzing` | `UploadPhase` + `UploadZone` | Drag-and-drop area, style picker, LLM toggle                        |
| `analyzed`           | `AnalyzePhase`               | Static analysis report, Generate Docstrings button                  |
| `generating`         | `GeneratePhase`              | Animated activity log, file status list                             |
| `done`               | `ReviewPhase`                | Coverage improvement banner, side-by-side diff, navigator, download |

`WorkflowPage.tsx` is the orchestrator — it calls all API endpoints, handles phase transitions, and renders whichever phase component is active.

### 4.3 Zustand Store — `sessionStore.ts`

```typescript
{
  phase: Phase; // 'idle' | 'analyzing' | 'analyzed' | 'generating' | 'done'
  sessionId: string | null; // backend session UUID returned by /upload
  sessionDir: string | null; // abs path to session workspace on the server
  report: AnalysisReport | null; // coverage stats + perFile + undocumentedList
  files: Record<string, FileData>; // originalContent + documentedContent + generatedRanges
  activeFile: string | null; // currently selected file in navigator
  docstringStyle: string; // 'google' | 'numpy' | 'rest' | 'epytext' | 'sphinx'
  llmProvider: "local" | "gemini"; // 'local' = Groq/Ollama; 'gemini' = Google Gemini
  docstringsAdded: number;
  coverageBefore: number;
  coverageAfter: number;
  qualityScore: number;
  error: string | null;
}
```

**Key actions:**

| Action                       | Effect                                                                                                                                    |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `startAnalyzing()`           | `phase → 'analyzing'`, clears error                                                                                                       |
| `setAnalysisComplete(...)`   | `phase → 'analyzed'`, stores sessionId, sessionDir, report, file paths                                                                    |
| `startGenerating()`          | `phase → 'generating'`                                                                                                                    |
| `setGenerationComplete(...)` | `phase → 'done'`, stores file contents + coverage delta                                                                                   |
| `setError(msg)`              | Sets error banner **and resets `phase → 'idle'`** (for fatal upload errors)                                                               |
| `setErrorOnly(msg)`          | Sets error banner **without changing phase** — used by generate failures so user stays on Inspect page and can retry without re-uploading |
| `reset()`                    | Resets entire store to `defaultState`                                                                                                     |

**Error banner behaviour:**

- When `sessionId && report` are present (user is past Inspect): shows **"Dismiss"** → calls `setErrorOnly('')`
- When no session (fatal error): shows **"Try Again"** → calls `reset()`

### 4.4 apiClient.ts

Thin typed wrapper around `fetch`. Key methods:

| Method                                    | Calls                | Returns                                               |
| ----------------------------------------- | -------------------- | ----------------------------------------------------- |
| `uploadProject(files, style)`             | `POST /upload`       | `UploadResponse` (session_id, session_dir, functions) |
| `rescan(sessionId, style)`                | `POST /rescan`       | `RescanResponse`                                      |
| `generateAll(sessionId, provider, style)` | `POST /generate/all` | quality_score, total_generated, warnings, errors      |
| `previewFile(sessionId, filePath)`        | `POST /preview`      | `{ file, content }`                                   |
| `getFileSource(sessionId, filePath)`      | `GET /file`          | `{ file, content }`                                   |
| `getCoverage(sessionDir, sessionId)`      | `GET /coverage`      | `CoverageResponse`                                    |
| `downloadProject(sessionId)`              | `GET /download/{id}` | triggers browser file download                        |

### 4.5 FunctionNavigator — `FunctionNavigator.tsx`

Left-panel navigator in the Review phase showing every class/function with a status dot:

| Dot      | Meaning                                                      | How determined                                                    |
| -------- | ------------------------------------------------------------ | ----------------------------------------------------------------- |
| 🟢 Green | Generated (new docstring added by this run)                  | block appears in `documentedContent` but not in `originalContent` |
| 🔵 Blue  | Pre-existing (docstring was already there before this run)   | block appears in both `originalContent` and `documentedContent`   |
| ⚪ Grey  | Skipped (engine did not generate; function has no docstring) | block absent from `documentedContent`                             |

The navigator uses `findDocstringBlocks()` (a lightweight triple-quote scanner) and `parseEntries()` (AST-like structure parser) — both run entirely client-side on the plain source strings, no backend call needed.

Clicking a function name scrolls the `ComparisonViewer` to that function's line.

### 4.6 ComparisonViewer — `ComparisonViewer.tsx`

Side-by-side diff renderer:

- Splits both `originalContent` and `documentedContent` line-by-line
- Highlights lines within `generatedRanges` with a green background
- Syncs vertical scroll position between the two panes
- Copy-to-clipboard buttons for both sides

`generatedRanges` are computed by `computeHighlightRanges(original, documented)` in `WorkflowPage.tsx`, which diffs the docstring blocks between the two source strings and returns `[{start, end}]` pairs for newly added blocks only.

### 4.7 AnalyzePhase — `AnalyzePhase.tsx`

The Inspect phase renders:

- **Coverage Report** (`CoverageReport.tsx`): donut chart, total/documented/undocumented counts, per-file breakdown sorted by worst coverage first
- **Improvement Banner** (`ImprovementBanner.tsx`): projected +X% coverage improvement estimate
- **Docstring Style selector** — radio buttons for 5 styles; changing selection triggers a `/rescan` call
- **Generate Docstrings** button — triggers `handleGenerate` in `WorkflowPage`

---

## 5. Data Flow — Full Request Cycle

```
Browser                             FastAPI Backend
  │                                       │
  │──POST /upload (multipart) ──────────► │  save files to _SESSIONS_DIR/<id>/workspace/
  │                                       │  AST parse + ConfidenceScorer
  │◄─ { session_id, session_dir,         │
  │      functions[] } ─────────────────│
  │                                       │
  │  [user reviews Inspect page]          │
  │                                       │
  │──POST /rescan ──────────────────────► │  re-parse + re-score with new style
  │◄─ { functions[] } ─────────────────│
  │                                       │
  │──POST /generate/all ────────────────► │  HybridDocstringEngine.generate_for_module()
  │                                       │    ConfidenceScorer.score()
  │                                       │    DocstringGenerator.generate_*()
  │                                       │    GroqProvider.generate_summary()  [optional]
  │                                       │    DocstringValidator.fix_docstring()
  │◄─ { results[], quality_score } ────│
  │                                       │
  │──for each file:                        │
  │  POST /preview ─────────────────────► │  _insert_docstrings() → return source string
  │◄─ { content } ─────────────────────│  (no disk write)
  │                                       │
  │  GET /file ──────────────────────────► │  return original source string
  │◄─ { content } ─────────────────────│
  │                                       │
  │  GET /coverage ──────────────────────► │  count documented functions
  │◄─ { coverage_before, coverage_after }│
  │                                       │
  │──GET /download/{session_id} ────────► │  _insert_docstrings() all files → zip → FileResponse
  │◄─ application/zip ─────────────────│
```

---

## 6. LLM Integration

The LLM is **optional** and **summary-only**:

- Activated automatically when `GROQ_API_KEY` is set in environment
- Falls back to Ollama (`LLM_BASE_URL`) if Groq fails to load
- Frontend can explicitly choose `gemini` provider (requires `GEMINI_API_KEY` on backend)
- The LLM receives **only** the function signature — no body, no variable names, no comments

```python
# Prompt sent to Groq
f"Write a single-sentence Python docstring summary for: {func_signature}"
# e.g. "Write a single-sentence Python docstring summary for: deposit(self, amount: float) -> float"

# Only the first sentence is used:
summary = response.strip().split('.')[0]
```

If the LLM call fails for any reason (timeout, rate limit, invalid key), the template summary placeholder is kept silently — the generation still succeeds.

---

## 7. Docstring Styles Supported

| Style   | Format                                                      |
| ------- | ----------------------------------------------------------- |
| Google  | `Args:\n    name (type): description`                       |
| NumPy   | `Parameters\n----------\nname : type\n    description`      |
| reST    | `:param name: description\n:type name: type\n:returns: ...` |
| Epytext | `@param name: description\n@type name: type\n@return: ...`  |
| Sphinx  | `:param type name: description\n:returns: ...`              |

---

## 8. Error Handling & Resilience

| Scenario                                      | Behaviour                                                                                       |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Upload of non-`.py` file                      | Silently skipped; session created only if at least one `.py` was valid                          |
| File parse error (SyntaxError in user's code) | Logged; file skipped; other files still processed                                               |
| LLM timeout / API error                       | Template summary used; generation continues                                                     |
| Generation failure (network, session expired) | Error banner shown; user stays on Inspect page (`setErrorOnly`); can retry without re-uploading |
| Fatal upload error                            | Error banner shown; `phase → 'idle'`; full reset                                                |
| `_resolve_safe_path` outside allowed roots    | `HTTP 403 Access denied`                                                                        |
| Session expired (> TTL)                       | `HTTP 404 Session not found`                                                                    |

---

## 9. CI / Pre-commit

- **CI**: `.github/workflows/ci.yml` — runs `pytest` on every push using Python 3.11
- **Pre-commit**: `src/autodocstring/integrations/precommit.py` + `.pre-commit-hooks.yaml` — can be wired as a pre-commit hook to auto-scan staged Python files before commit
