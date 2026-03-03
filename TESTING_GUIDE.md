# Testing Guide (UI + API)

This guide covers the current, supported workflow using the FastAPI backend and the web UI.

## 1) Environment Setup

```bash
# Backend dependencies
pip install -e .

# Frontend dependencies
cd project/frontend
npm install
```

## 2) Backend Smoke Test

Start the API server:

```bash
python -m uvicorn autodocstring.api.app:app --reload --port 8001 --app-dir src
```

Verify the API is up:

```bash
curl http://localhost:8001/openapi.json
```

## 3) Web UI Flow (Manual)

1. Start the UI:

```bash
cd project/frontend
npm run dev
```

2. Open the UI in a browser and upload a Python project.
3. Select the docstring style (Google/NumPy/reST).
4. Run scan and confirm coverage updates.
5. Generate docstrings and verify the review pane shows new docstrings.
6. Accept changes and export a patch.

## 4) Backend Tests

Run the Python test suite:

```bash
pytest
```

## 5) Optional Pre-commit Check

If you use pre-commit, add the hook in `.pre-commit-config.yaml` and run:

```bash
pre-commit run --all-files
```
