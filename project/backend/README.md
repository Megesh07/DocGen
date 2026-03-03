# AutoDocstring Backend

FastAPI backend for the Automated Python Docstring Generator.

## Setup

```bash
# From the project root
pip install -e ".[dev]"
python -m uvicorn autodocstring.api.app:app --reload --port 8001 --app-dir src
```

- API: http://localhost:8001
- Swagger UI: http://localhost:8001/docs

## Structure

The backend source lives in `src/autodocstring/`:

```
src/autodocstring/
├── api/         # FastAPI routes and Pydantic schemas
├── parser/      # AST-based Python source parser
├── confidence/  # Deterministic confidence scorer
├── generator/   # Docstring template engine + LLM providers
├── validation/  # Style checker and completeness validator
├── safety/      # Idempotent file writer with rollback
├── session/     # UUID session management
├── models/      # Shared data models
├── config/      # pyproject.toml config loader
└── utils/       # File utilities
```
