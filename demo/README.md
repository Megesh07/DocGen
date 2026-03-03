# Demo Files

Three Python files designed to showcase the tool's three core scenarios during a live demonstration.

---

## Files

| File | Scenario | Starting Coverage |
|---|---|---|
| `calculator.py` | Zero docstrings — completely undocumented | 0 % |
| `user_service.py` | Partial docstrings — summaries only, missing Args/Returns | ~20 % |
| `utils.py` | Style mismatch — NumPy style in a Google-style project | 0 % validated |

---

## Live Demo Steps

### 1. Scan the `demo/` folder

In the web UI, paste the absolute path to this `demo/` folder and click **Scan**.

```
<project-root>/demo
```

You will see all three files listed with their functions and current docstring status.

---

### 2. Scenario A – Zero docstrings (`calculator.py`)

- All 13 functions/methods show **Missing** status.
- Click **Generate** → watch every function get a complete Google-style docstring.
- Coverage jumps from **0 % → 100 %**.

---

### 3. Scenario B – Partial docstrings (`user_service.py`)

- Functions show **Incomplete** status — summary exists but Args/Returns are absent.
- Click **Generate** → the tool upgrades each stub in-place without overwriting the existing summary.
- Coverage upgrades to **100 % complete**.

---

### 4. Scenario C – Style mismatch (`utils.py`)

- All 4 functions are documented in NumPy style.
- Scanner (running in Google mode) flags them as **Style Mismatch**.
- Click **Generate** → docstrings are rewritten in Google format.
- Show the diff view to highlight the before/after change.

---

## Reset

To revert files back to their original state for a repeat demo, use git:

```bash
git checkout demo/
```
