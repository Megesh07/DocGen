# Architecture — DocGen (Automated Python Docstring Generator)

## 1. Overview

DocGen is a full-stack web application that automatically generates, reviews, and applies Python docstrings. It follows a clean three-tier architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (React/TypeScript)                │
│            Vite dev server  ·  localhost:5173                │
└────────────────────────┬────────────────────────────────────┘
                         │  REST (JSON over HTTP)
┌────────────────────────▼────────────────────────────────────┐
│               FastAPI Backend (Python 3.11+)                 │
│               Uvicorn ASGI  ·  localhost:8001                │
└────────────────────────┬────────────────────────────────────┘
                         │  HTTPS
┌────────────────────────▼────────────────────────────────────┐
│              Groq Cloud LLM API (optional)                   │
│           llama-3.3-70b-versatile  (summary only)            │
└─────────────────────────────────────────────────────────────┘
```

The backend is entirely stateless per request. Session state is persisted to disk (`.autodocstring_sessions/<id>/`) so the browser can resume a workflow across page refreshes.

---

## 2. Repository Structure

```
DocGen/
├── src/
│   └── autodocstring/          # Backend Python package
│       ├── api/                # FastAPI routes + Pydantic schemas
│       ├── parser/             # AST-based Python source analysis
│       ├── generator/          # Docstring generation engines + templates
│       ├── confidence/         # Risk scoring (offline, deterministic)
│       ├── safety/             # Safe file writer with rollback
│       ├── validation/         # Style checker (Google / NumPy / reST …)
│       ├── session/            # Session lifecycle management
│       ├── models/             # Shared data models (dataclasses)
│       ├── integrations/       # Pre-commit hook helper
│       └── utils/              # Shared helpers
│
├── project/
│   └── frontend/               # React/TypeScript SPA
│       ├── src/
│       │   ├── components/     # Phase components + Navigator + Viewer
│       │   └── store/          # Zustand global state (sessionStore.ts)
│       ├── package.json
│       └── vite.config.ts
│
├── tests/                      # pytest test suite
├── demo/                       # Example Python files (5 categories)
├── docs/                       # Project documentation
├── .github/workflows/ci.yml    # GitHub Actions CI
├── pyproject.toml              # Python package metadata + deps
└── README.md
```

---

## 3. Backend Architecture

### 3.1 API Layer — `src/autodocstring/api/`

**`app.py`** — 1200-line FastAPI application with the following endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/health` | Health check (LLM availability, session count, uptime) |
| POST | `/api/v1/session` | Create a new session, upload `.py` files |
| POST | `/api/v1/upload` | Upload files via multipart form-data |
| POST | `/api/v1/scan` | Analyse uploaded files, return coverage report |
| POST | `/api/v1/generate` | Generate docstrings for all undocumented functions |
| POST | `/api/v1/apply` | Write generated docstrings into session files |
| POST | `/api/v1/review` | Return diff between original and documented content |
| POST | `/api/v1/undo` | Revert a file to its original content |
| GET | `/api/v1/download/{session_id}` | Download documented files as a ZIP |

**Key design decisions in `app.py`:**
- `_docstring_status()` — determines whether an existing docstring is "complete and correct style" or needs regeneration. A docstring counts as valid only when BOTH style-match AND completeness checks pass.
- `_build_signature()` — builds a human-readable function signature string (`add(self, a: int, b: int) -> int`) sent to the frontend so the AnalyzePhase can show which params/returns are missing without deserialising full metadata.
- All modifications are made in **session copies** of files, never the originals on disk.

**`schemas.py`** — Pydantic v2 models for every request and response.

### 3.2 Parser — `src/autodocstring/parser/`

**`ast_parser.py`** — Walks the Python AST and returns a `ModuleMetadata` object containing:
- Module-level docstring
- Top-level `FunctionMetadata` objects
- `ClassMetadata` objects, each containing `FunctionMetadata` for methods

**`extractors.py`** — Extracts:
- Parameter names, type hints, default values
- Return type annotation
- Decorators (`@staticmethod`, `@classmethod`, `@property`)
- Whether the function is asynchronous (`async def`)
- `# autodoc: ignore` directive detection

### 3.3 Generator — `src/autodocstring/generator/`

Two engines are provided:

#### `DocstringGenerator` (deterministic, pure template)
- Instantiated with a style (`google`, `numpy`, `rest`, `epytext`, `sphinx`)
- Selects the matching `BaseTemplate` subclass from `generator/templates/`
- Renders full docstrings: summary placeholder → Args section → Returns section → Raises section
- No network calls, always produces output

#### `HybridDocstringEngine` (production engine)
The full pipeline per function:

```
FunctionMetadata
       │
       ▼
[1] # autodoc: ignore directive?  ──YES──► skip (generation_type="skipped")
       │ NO
       ▼
[2] docstring already present & rewrite_existing=False?  ──YES──► skip
       │ NO
       ▼
[3] ConfidenceScorer.score(metadata)
       │
       ├─ confidence < 0.60 ──► skip (low confidence)
       │
       ▼
[4] DocstringGenerator.generate_function_docstring(metadata)
       │   (deterministic template render)
       ▼
[5] LLM provider available?
       ├─ YES → send only the function stub + existing summary to Groq
       │         receive one-sentence summary; replace template placeholder
       │         generation_type = "llm_enhanced"
       └─ NO  → keep template summary
               generation_type = "template"
       ▼
DocstringResult(docstring, confidence, risk, generation_type, reason)
```

**`groq_provider.py`** — HTTP client for the Groq OpenAI-compatible endpoint:
- Model: `llama-3.3-70b-versatile`
- Only the **summary sentence** is generated by the LLM. All structured sections (Args, Returns, Raises) are always rendered by the deterministic template to prevent hallucination of parameter names or types.
- Falls back gracefully if the API key is absent or the request times out (45 s timeout).

**`_derive_class_summary()`** — Deterministic class summary helper (no LLM):
- Splits CamelCase class name into words
- Maps suffixes via a lookup table (`Processor → "Processes"`, `Manager → "Manages"`, `Calculator → "Provides ... functionality"`, etc.)
- Falls back to listing public method names for context

**Templates** (`generator/templates/`):
Each template (`GoogleTemplate`, `NumpyTemplate`, `RestTemplate`, `EpytextTemplate`, `SphinxTemplate`) inherits from `BaseTemplate` and implements:
- `generate_function_docstring(metadata)` → full formatted docstring string
- `generate_class_docstring(metadata)` → class docstring string

### 3.4 Confidence Scorer — `src/autodocstring/confidence/scorer.py`

Stateless, offline, purely deterministic. Starts at `confidence = 1.0` and applies penalties:

| Condition | Penalty |
|-----------|---------|
| Each parameter without a type hint | −0.05 |
| No return type annotation | −0.10 |
| AST branch count > 8 (if/for/while/try/BoolOp) | −0.10 |
| Generator function (`yield`) | −0.05 |
| External call to non-whitelisted module | −0.05 |

**Decision thresholds:**
- `confidence ≥ 0.85` → `AUTO_APPLY` (safe, apply automatically)
- `0.60 ≤ confidence < 0.85` → `REVIEW` (generate but flag for human review)
- `confidence < 0.60` → skip entirely

### 3.5 Safety Applier — `src/autodocstring/safety/applier.py`

`SafeApplier` writes docstrings into source files with four safety guarantees:
1. **Idempotency** — if the existing docstring already matches, the file is not touched
2. **Syntax safety** — after each write, `ast.parse()` is called; on `SyntaxError` the original content is restored automatically
3. **Non-intrusive** — only docstring statement nodes are replaced; imports, comments, blank lines, and formatting are untouched
4. **Dry-run mode** — can return a unified diff without writing anything

`_insert_docstrings()` walks the AST and handles `ast.FunctionDef`, `ast.AsyncFunctionDef`, and `ast.ClassDef` nodes.

### 3.6 Session Manager — `src/autodocstring/session/`

Each workflow run gets a UUID session. The session directory (`.autodocstring_sessions/<id>/`) stores:
- `metadata.json` — session info (created at, file list, style, LLM provider)
- `original/<file>` — unmodified copies of all uploaded files
- `current/<file>` — working copies (modified by generate/apply steps)
- `generation_cache.json` — cached `DocstringResult` objects to avoid re-generating

Background cleanup task deletes sessions older than 2 hours to prevent disk accumulation.

### 3.7 Validation — `src/autodocstring/validation/`

`style_checker.py` contains:
- `is_style_match(docstring, style, metadata)` — detects the docstring's format (presence of `Args:`, `:param`, `Parameters\n---`, etc.) and checks it matches the requested style
- `is_complete(docstring, metadata)` — verifies all non-self/cls parameters are documented and Returns is present if a return type is annotated

---

## 4. Frontend Architecture

### 4.1 Technology Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 18 + TypeScript |
| Build tool | Vite 5 |
| State management | Zustand (`sessionStore.ts`) |
| HTTP client | `apiClient.ts` (thin fetch wrapper) |
| Styling | Inline styles with CSS variables (`--bg-page`, `--text-primary`, etc.) |
| Linting | ESLint 9 (flat config) |

### 4.2 Workflow Phase Model

The UI is a **linear 5-phase wizard** controlled by the `phase` field in `sessionStore`:

```
Upload → Inspect (Analyze) → Generate → Review → [New Upload]
  1           2                  3          4
```

Each phase is a separate component:

| Phase | Component | Purpose |
|-------|-----------|---------|
| 1 | `UploadPhase.tsx` + `UploadZone.tsx` | Drag-and-drop Python file upload, style selector |
| 2 | `AnalyzePhase.tsx` | Scan results, per-file coverage, undocumented function list |
| 3 | `GeneratePhase.tsx` | Real-time activity log animation, triggers `/generate` + `/apply` |
| 4 | `ReviewPhase.tsx` | Side-by-side diff viewer, coverage report, download |
| — | `WorkflowPage.tsx` | Orchestrator: calls all API endpoints, manages phase transitions |

### 4.3 Zustand Store — `sessionStore.ts`

Key fields:

```typescript
{
  sessionId: string | null          // backend session UUID
  phase: 1 | 2 | 3 | 4            // current workflow phase
  files: Record<string, FileData>  // originalContent + documentedContent + generatedRanges
  report: ScanReport | null        // coverage stats, undocumentedList, perFile
  docstringStyle: string           // 'google' | 'numpy' | 'rest' | 'epytext' | 'sphinx'
  llmProvider: 'local' | 'gemini' // maps to Groq API in backend
  uploadedFilenames: string[]
}
```

`FileData` contains:
- `originalContent` — source before generation (used by diff viewer and navigator dots)
- `documentedContent` — source after generation
- `generatedRanges` — `[startLine, endLine][]` pairs highlighting new docstrings in the diff viewer

### 4.4 FunctionNavigator — `FunctionNavigator.tsx`

Left-panel navigator showing every class/function across all files with a status dot:

| Dot colour | Meaning | How determined |
|------------|---------|---------------|
| 🟢 Green | Generated (new docstring added) | `hasDoc && !hadDocOriginal` |
| 🔵 Blue | Pre-existing (docstring was already there) | `hasDoc && hadDocOriginal` |
| ⚪ Grey | Skipped (engine did not generate) | `!hasDoc` |

Both `parseEntries()` and `findDocstringBlocks()` run on the plain source string (no backend call needed), making the navigator purely client-side.

### 4.5 ComparisonViewer — `ComparisonViewer.tsx`

Side-by-side diff renderer that:
- Splits both original and documented content line-by-line
- Highlights `generatedRanges` with a green background
- Syncs scroll position between the two panes
- Provides copy-to-clipboard for both sides

---

## 5. Data Flow — Full Request Cycle

```
Browser                        FastAPI Backend
  │                                   │
  │──POST /api/v1/session ──────────► │  create session dir
  │◄─ { session_id } ────────────────│
  │                                   │
  │──POST /api/v1/scan ─────────────► │  ast_parser → ModuleMetadata
  │                                   │  _docstring_status() per function
  │◄─ ScanResponse ──────────────────│  (totalFunctions, documented, perFile)
  │                                   │
  │──POST /api/v1/generate ─────────► │  HybridDocstringEngine.generate_for_module()
  │                                   │     ConfidenceScorer.score()
  │                                   │     DocstringGenerator.generate_*()
  │                                   │     GroqProvider.generate_summary()  [optional]
  │◄─ GenerateResponse ──────────────│  { results: DocstringResult[] }
  │                                   │
  │──POST /api/v1/apply ────────────► │  SafeApplier.apply_to_file()
  │                                   │     ast.parse() safety check
  │◄─ ApplyResponse ─────────────────│  { applied, skipped, documentedContent }
  │                                   │
  │──GET /api/v1/download/{id} ─────► │  zip session current/ files
  │◄─ application/zip ───────────────│
```

---

## 6. LLM Integration

The LLM is **optional** and **summary-only**:

- Activated when `GROQ_API_KEY` environment variable is set
- Model: `llama-3.3-70b-versatile` (configurable via `LLM_MODEL` env var)
- The backend sends only: the function name, parameter names, and return type — **never the function body**
- The LLM returns exactly one sentence which replaces the template placeholder summary
- If the LLM call fails (timeout, rate limit, invalid key), the template summary is kept silently — the generation still succeeds

```python
# What is sent to Groq (pseudocode)
prompt = f"Write a single-sentence Python docstring summary for: {func_signature}"

# What is used from the response
summary_sentence = response.strip().rstrip('.')
```

---

## 7. Docstring Styles Supported

| Style | Format example |
|-------|---------------|
| Google | `Args:\n    name (type): description` |
| NumPy | `Parameters\n----------\nname : type\n    description` |
| reST | `:param name: description\n:type name: type\n:return: ...` |
| Epytext | `@param name: description\n@type name: type\n@return: ...` |
| Sphinx | `:param type name: description\n:returns: ...` |

---

## 8. CI / Pre-commit

- **CI**: `.github/workflows/ci.yml` — runs `pytest` on every push using Python 3.11
- **Pre-commit**: `integrations/precommit.py` + `.pre-commit-hooks.yaml` — can be wired as a pre-commit hook to auto-scan staged Python files before commit
