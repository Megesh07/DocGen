# Demo Files

Four Python files that together exercise every scenario the DocGen model handles.  
Upload **all four at once** (multi-file upload) or try them individually.

---

## File Overview

| File | What it demonstrates | Expected outcome |
|------|---------------------|-----------------|
| `01_clean_slate.py` | Fully typed, zero docstrings | 100 % coverage, all AUTO_APPLY |
| `02_mixed_state.py` | Pre-existing docs + `# autodoc: ignore` + undocumented | Preserves existing, skips ignored, generates the rest |
| `03_confidence_stress.py` | Missing types, high branches, generators, `*args/**kwargs` | Mix of AUTO_APPLY, REVIEW-flagged, and skipped |
| `04_edge_cases.py` | `@dataclass`, `@property`, ABC, context manager, `async` generator, nested functions, `Union`/`Optional`, `pass`/`raise`-only | Parser handles every pattern; docstrings generated for all |

---

## File Details

### `01_clean_slate.py` — Best Case
Every function and method is fully type-annotated with no docstrings.  
This is the ideal input: the model will generate docstrings for every item with **maximum confidence** (≥ 0.85, AUTO_APPLY).

Patterns inside:
- Standalone functions: `add`, `divide`, `clamp`, `is_prime`, `format_currency`, `find_median`
- `async def` function: `fetch_exchange_rate`
- Full class: `BankAccount` — `__init__`, instance methods, `@property`, `@staticmethod`, `@classmethod`

---

### `02_mixed_state.py` — Real-World File
Simulates a codebase that is partially documented — exactly what you'd find in a real project.

| Item | State | What happens |
|------|-------|-------------|
| `read_file`, `slugify` | Complete Google-style docstring | **Preserved** — shown with blue dot in navigator |
| `EmailService.validate_address` | Complete docstring on a method | **Preserved** |
| `_internal_checksum`, `_LegacyAdapter` | `# autodoc: ignore` directive | **Skipped** — grey dot, not touched |
| `write_json`, `paginate`, `retry` | No docstring | **Generated** — green dot |
| `EmailService.send`, `.get_sent_count`, `.bulk_send` | No docstring | **Generated** — green dot |

---

### `03_confidence_stress.py` — Confidence Scoring
Each function is crafted to hit specific penalty thresholds in `ConfidenceScorer`.

| Function | Penalties applied | Approx. score | Decision |
|----------|------------------|---------------|---------|
| `celsius_to_fahrenheit` | none | 1.00 | AUTO_APPLY |
| `truncate` | none | 1.00 | AUTO_APPLY |
| `calculate_discount` | −0.15 (3 untyped) + −0.10 (no return) | 0.75 | REVIEW |
| `merge_dicts` | −0.15 (3 untyped) + −0.10 (no return) | 0.75 | REVIEW |
| `classify_http_status` | −0.10 (11 branches) | 0.90 | AUTO_APPLY |
| `validate_config` | −0.05 (1 untyped) + −0.10 (10 branches) | 0.85 | AUTO_APPLY |
| `fibonacci` | −0.05 (generator) | 0.95 | AUTO_APPLY |
| `chunk` | −0.05 (generator) | 0.95 | AUTO_APPLY |
| `log_event` | −0.10 (2 untyped variadic) | 0.90 | AUTO_APPLY |
| `build_query` | −0.15 (3 untyped) + −0.10 (no return) | 0.75 | REVIEW |

Functions in the REVIEW zone will be **generated but highlighted** in the review panel — you should inspect them before applying.

---

### `04_edge_cases.py` — Parser Stress Test
Tests the AST parser and `SafeApplier` on constructs that trip up naive docstring tools.

| Pattern | Class / Function |
|---------|-----------------|
| `@dataclass` with `field()` | `Point` |
| `__repr__`, `__eq__` dunder methods | `Point` |
| `@abstractmethod` | `Serializer.serialize`, `.deserialize` |
| `@property` getter | `Temperature.celsius`, `.fahrenheit`, `.kelvin` |
| `@property.setter` | `Temperature.celsius` setter |
| `__enter__` / `__exit__` | `Timer` |
| `async def` generator (`yield` inside `async def`) | `fetch_pages` |
| `async def` with inner `async def` | `gather_results` → `_fetch_one` |
| Closure / inner function | `memoize` → `wrapper`, `make_multiplier` → `multiplier` |
| `Union[str, int, float]` param | `parse_int` |
| `Optional[int]` return | `parse_int` |
| `pass`-only body | `not_implemented_yet` |
| `raise NotImplementedError`-only body | `must_override` |
| `__len__`, `__contains__`, `__iter__` | `TagRegistry` |

---

## Recommended Workflow for Live Demo

1. Open `http://localhost:5173`
2. Upload all 4 files at once
3. Select **Google** style
4. Click **Analyze** — observe coverage stats for each file
5. Click **Generate Docstrings**
6. In the Review phase:
   - Check the **navigator dots**: green (generated), blue (pre-existing), grey (skipped)
   - Note `02_mixed_state.py` — blue dots on already-documented functions
   - Note that `_internal_checksum` and `_LegacyAdapter` show grey (ignored)
   - Note `03_confidence_stress.py` — any REVIEW-flagged functions
7. Download the documented ZIP and open the files to verify output
