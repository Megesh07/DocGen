# Testing Guide — DocGen

## 1. Quick Start

```bash
# Install the package + all dev dependencies
pip install -e ".[dev]"

# Run the full test suite
pytest

# Run with coverage report
pytest --cov=src/autodocstring --cov-report=term-missing

# HTML coverage report (open htmlcov/index.html)
pytest --cov=src/autodocstring --cov-report=html
```

`[dev]` extras include: `pytest`, `pytest-cov`, `black`, `mypy`, `flake8`, `httpx`.

---

## 2. Test Structure

```
tests/
├── __init__.py
├── conftest.py             # Shared fixtures (sample files, temp dirs, mock providers)
├── test_api.py             # FastAPI endpoint integration tests (TestClient)
├── test_confidence.py      # ConfidenceScorer unit tests
├── test_generator.py       # DocstringGenerator + HybridDocstringEngine tests
├── test_parser.py          # AST parser + extractor tests
├── test_safety.py          # _insert_docstrings / SafeApplier behaviour tests
├── test_validation.py      # Style checker + completeness checker tests
├── fixtures/               # Static input files for tests
└── sample_project/         # Multi-file Python project used in integration tests
    ├── calc.py
    ├── math_utils.py
    ├── string_utils.py
    ├── syntax_error.py     # Intentionally broken file (tests error handling)
    ├── api/
    ├── async_ops/
    ├── core/
    ├── data/
    ├── decorators/
    ├── hard_cases/
    ├── legacy/
    └── utils/
```

---

## 3. What is Tested

### `test_parser.py`

Tests `ast_parser.py` and `extractors.py`:

- Extracts class names, method names, function names
- Correctly identifies parameter names, type hints, defaults, `*args` / `**kwargs`
- Detects `async def` functions
- Detects decorators: `@staticmethod`, `@classmethod`, `@property`
- Returns module-level docstring when present
- Handles files with syntax errors gracefully (returns empty metadata, not an exception)
- Detects `# autodoc: ignore` directive

### `test_confidence.py`

Tests `ConfidenceScorer`:

- Fully annotated function scores ≥ 0.85 (`AUTO_APPLY`)
- Each untyped parameter decreases score by 0.05
- Missing return annotation reduces score by 0.10
- Branch count > 8 applies −0.10 penalty
- Generator functions (`yield`) apply −0.05 penalty
- Threshold buckets correctly assigned (`AUTO_APPLY`, `REVIEW`, `SKIP`)
- Built-in whitelist (`print`, `len`, `range`, …) does not trigger external-call penalty

### `test_generator.py`

Tests `DocstringGenerator` and `HybridDocstringEngine`:

- Google style renders `Args:`, `Returns:`, `Raises:` sections
- NumPy style renders dashed underlines under section headers
- reST style uses `:param name:` syntax
- Epytext style uses `@param name:` syntax
- Sphinx style uses `:param type name:` syntax
- Functions with no parameters omit the Args section
- Functions with no return annotation omit the Returns section
- `# autodoc: ignore` directive skips generation (`generation_type="skipped"`)
- `rewrite_existing=False` skips functions that already have a docstring
- `HybridDocstringEngine` falls back to template when no LLM provider is configured
- Template summary placeholder is replaced when LLM provider returns a result

### `test_safety.py`

Tests `_insert_docstrings()` / `SafeApplier`:

- Applies a valid docstring and the result parses cleanly with `ast.parse()`
- Idempotent: applying the same docstring twice does not double-insert it
- Rolls back to original content when the generated docstring would cause a syntax error
- Dry-run mode returns modified source as a string without writing to disk
- Handles `@property`, `async def`, `@staticmethod`, nested functions

### `test_api.py`

Integration tests using `httpx.TestClient`:

- `GET /api/v1/health` returns `200` with `status: "healthy"`
- `POST /api/v1/upload` with valid `.py` files returns coverage stats and `session_id`
- `POST /api/v1/upload` with no `.py` files returns `HTTP 400`
- `POST /api/v1/rescan` updates scan results when style changes
- `GET /api/v1/file` returns file source for a valid session file
- `POST /api/v1/preview` returns source with docstrings injected (no disk write)
- `POST /api/v1/generate/all` returns `quality_score`, `total_generated`, `warnings`, `errors`
- `GET /api/v1/download/{id}` returns a valid ZIP file
- Session isolation: two concurrent sessions do not share file state
- Expired session returns `HTTP 404`
- Path outside sandbox returns `HTTP 403`

### `test_validation.py`

Tests `style_checker.py` and `DocstringValidator`:

- `is_style_match()` correctly identifies Google, NumPy, reST, Epytext, and Sphinx docstrings
- `is_complete()` returns `False` when a parameter is undocumented
- `is_complete()` returns `True` when all params and Returns are documented
- Style mismatch (e.g. Google-style checked against NumPy) returns `False`
- `fix_docstring()` adds missing trailing period, removes extra blank lines

---

## 4. Fixtures (`conftest.py`)

| Fixture                 | Type               | Description                                            |
| ----------------------- | ------------------ | ------------------------------------------------------ |
| `tmp_py_file(content)`  | factory            | Creates a temp `.py` file; deleted after test          |
| `sample_function_meta`  | `FunctionMetadata` | Fully annotated function with 2 params and return type |
| `untyped_function_meta` | `FunctionMetadata` | Same function with no type hints                       |
| `mock_groq_provider`    | mock               | Returns a fixed one-sentence summary                   |
| `test_client`           | `TestClient`       | FastAPI test client with isolated temp session dir     |

---

## 5. Running Specific Tests

```bash
# All tests, verbose
pytest -v

# One file
pytest tests/test_parser.py -v

# One class
pytest tests/test_generator.py::TestHybridEngine -v

# Keyword match
pytest -k "confidence" -v

# Stop on first failure
pytest -x

# Show 5 slowest tests
pytest --durations=5
```

---

## 6. Type Checking & Linting

```bash
# Static type checking
mypy src/autodocstring

# Linting
flake8 src/autodocstring

# Format check (does not modify files)
black --check src/autodocstring

# Auto-format
black src/autodocstring

# Frontend TypeScript check
cd project/frontend
npx tsc --noEmit
```

---

## 7. Testing the Demo Files

The `demo/` directory contains 4 files covering every generation scenario — ideal for manual end-to-end testing:

| File                      | What to expect                                                                                                |
| ------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `01_clean_slate.py`       | 15 functions/methods · 0 % starting coverage · all AUTO_APPLY → 100 % after generate                          |
| `02_mixed_state.py`       | Mix of documented + undocumented; `# autodoc: ignore` entries skipped; pre-existing docstrings preserved      |
| `03_confidence_stress.py` | Missing type hints, high branch counts, generators → some REVIEW-flagged, some skipped                        |
| `04_edge_cases.py`        | `@dataclass`, `@property`, `@abstractmethod`, `async` generator, closures, Union/Optional, `pass`-only bodies |

**Upload via UI:**

1. Open `http://localhost:5173`
2. Drag all four files into the upload zone
3. Choose a style and click **Inspect**
4. Click **Generate Docstrings**
5. Verify: green dots on all `01_clean_slate.py` functions, blue/grey on `02_mixed_state.py` existing docs

**Command-line scan (no web UI):**

```bash
python -m autodocstring scan demo/01_clean_slate.py --style google
```

---

## 8. Continuous Integration

Tests run automatically on GitHub Actions for every `push`:

- Python version: **3.11**
- Command: `pytest --tb=short`
- Workflow: `.github/workflows/ci.yml`

Reproduce locally:

```bash
pip install -e ".[dev]"
pytest --tb=short
```

Coverage target: **≥ 80 %** for all non-trivial modules. The `safety/` and `confidence/` modules are fully deterministic and target **≥ 95 %**.
