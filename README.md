# DocGen — Automated Python Docstring Generator

A FastAPI + React tool that analyses Python source files, generates docstrings using AST and optional LLM, and lets you review a side-by-side diff before downloading the documented project.

---

## Backend

```bash
pip install -e .
python -m uvicorn autodocstring.api.app:app --reload --port 8001 --app-dir src
```

API available at: http://localhost:8001  
Swagger UI: http://localhost:8001/docs

---

## Frontend

```bash
cd project/frontend
npm install
npm run dev
```

UI available at: http://localhost:5173

---

## Tests

```bash
pytest
```
