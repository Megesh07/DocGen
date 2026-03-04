"""FastAPI application – fully operational hardened REST backend."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Response, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from autodocstring.api.schemas import (
    ScanRequest,
    GenerateRequest,
    RescanRequest,
    ReviewRequest,
    ApplyRequest,
    UndoRequest,
    UndoResponse,
    DocstringResultSchema,
    ScanResponse,
    ExpandedCoverageStats,
    SessionResponse,
)
from autodocstring.session.session_manager import (
    get_session_manager,
    schedule_background_cleanup,
    compute_file_hash,
)
from autodocstring.confidence.scorer import AUTO_APPLY, REVIEW

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT: Path = Path(os.getcwd()).resolve()
MAX_FUNCTIONS_PER_REQUEST: int = 2000
_API_VERSION = "2.0.0"
_start_time: datetime = datetime.utcnow()
_ALLOWED_STYLES = {"google", "numpy", "rest", "epytext", "sphinx"}

# Resolved sessions root — may live outside PROJECT_ROOT on cloud deployments
# (e.g. Render sets SESSION_DIR=/tmp). We import the same env-driven value used
# by the session manager so the sandbox check stays in sync.
from autodocstring.session.session_manager import _SESSIONS_DIR as _SM_SESSIONS_DIR
_SESSIONS_ROOT: Path = _SM_SESSIONS_DIR.resolve()


def _normalize_style(style: Optional[str]) -> str:
    style_value = (style or "google").strip().lower()
    return style_value if style_value in _ALLOWED_STYLES else "google"


def _build_signature(func) -> str:
    """Build a human-readable signature string from FunctionMetadata.

    The signature is returned to the frontend inside every scan result so that
    the AnalyzePhase can compute accurate ``missingParams`` and
    ``missingReturns`` metrics without needing the full metadata object.

    Example output::

        "add(self, a: int, b: int) -> int"
        "run()"

    Args:
        func: FunctionMetadata instance.

    Returns:
        Formatted signature string.
    """
    parts = []
    for p in func.parameters:
        if p.type_hint:
            parts.append(f"{p.name}: {p.type_hint}")
        else:
            parts.append(p.name)
    ret = f" -> {func.return_type}" if func.return_type else ""
    return f"{func.name}({', '.join(parts)}){ret}"


def _docstring_status(docstring: str, metadata, style: str) -> tuple[bool, str]:
    """Determine whether an existing docstring satisfies the requested style.

    A docstring is considered fully valid only when BOTH conditions hold:
    1. ``is_style_match`` — the docstring follows the chosen style's section
       format (or the function has no documentable elements, making any
       non-trivial summary acceptable in every style).
    2. ``is_complete``   — all non-self/cls parameters are documented and, if
       the function has a non-void return type, a Returns section is present.

    Anything less (wrong style, partial docs, missing Returns) is treated as
    *undocumented* so the engine regenerates a fresh docstring.

    Args:
        docstring: Existing docstring text extracted by the AST parser.
        metadata: FunctionMetadata object for the function being checked.
        style: User-requested style (``google``, ``numpy``, ``rest``, etc.).

    Returns:
        (True, reason) when docstring is fully valid; (False, reason) when
        the docstring needs to be regenerated.
    """
    if not docstring or not docstring.strip():
        return False, "no docstring"
    from autodocstring.validation.style_checker import is_style_match, is_complete
    # Pass metadata so is_style_match can apply the no-section shortcut
    if is_style_match(docstring, style, metadata=metadata) and is_complete(docstring, metadata):
        return True, "docstring matches style and is complete"
    # Provide a more informative reason for debugging/UI display
    if not is_style_match(docstring, style, metadata=metadata):
        reason = f"style mismatch (has docstring but not {style!r} format)"
    else:
        reason = "incomplete (missing parameters or returns documentation)"
    return False, reason

# ---------------------------------------------------------------------------
# FastAPI lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    from autodocstring.safety.transaction import recover_orphan_backups
    recovered = recover_orphan_backups()
    if recovered:
        logger.warning("Startup crash recovery: restored %d transaction(s): %s", len(recovered), recovered)

    manager = get_session_manager()
    cleanup_task = schedule_background_cleanup(manager)
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

# ---------------------------------------------------------------------------
# App and router setup
# ---------------------------------------------------------------------------

app = FastAPI(title="AutoDocstring API", version=_API_VERSION, lifespan=lifespan)

_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix="/api/v1")

# ---------------------------------------------------------------------------
# Locks and Sandbox
# ---------------------------------------------------------------------------

_file_locks: Dict[str, asyncio.Lock] = {}

async def _get_file_lock(path: str) -> asyncio.Lock:
    if path not in _file_locks:
        _file_locks[path] = asyncio.Lock()
    return _file_locks[path]

def _release_file_lock(path: str) -> None:
    _file_locks.pop(path, None)

def _resolve_safe_path(raw_path: str) -> Path:
    try:
        resolved = Path(raw_path).resolve()
    except (ValueError, OSError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid path: {e}")

    # Allow paths that live under the project root OR under the sessions
    # directory (which may be /tmp or another location on cloud deployments).
    in_project = False
    try:
        resolved.relative_to(PROJECT_ROOT)
        in_project = True
    except ValueError:
        pass

    if not in_project:
        try:
            resolved.relative_to(_SESSIONS_ROOT)
            in_project = True
        except ValueError:
            pass

    if not in_project:
        raise HTTPException(status_code=403, detail="Access denied")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    return resolved

def _build_provider(name: str):
    if name == "local":
        # Prefer Groq when GROQ_API_KEY is present; fall back to Ollama.
        if os.getenv("GROQ_API_KEY"):
            try:
                from autodocstring.generator.groq_provider import GroqProvider
                return GroqProvider()
            except Exception as e:
                print(f"Failed to load GroqProvider: {e}")
                # Fall through to Ollama below
        try:
            from autodocstring.generator.ollama_provider import OllamaProvider
            _base = os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
            if _base.endswith("/api/generate"):
                _base = _base[: -len("/api/generate")]
            return OllamaProvider(url=_base + "/api/generate")
        except Exception as e:
            print(f"Failed to load OllamaProvider: {e}")
            return None
    elif name == "gemini":
        try:
            from autodocstring.generator.gemini_provider import GeminiProvider
            # Checks for GEMINI_API_KEY inside the class
            return GeminiProvider()
        except Exception as e:
            print(f"Failed to load GeminiProvider: {e}")
            return None
    return None

def _result_to_schema(r) -> DocstringResultSchema:
    return DocstringResultSchema(**r.to_dict())

# ---------------------------------------------------------------------------
# POST /api/v1/scan
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=ScanResponse, summary="Upload files and create a session")
async def upload_files(
    files: List[UploadFile] = File(...),
    style: str = Form("google"),
) -> ScanResponse:
    from autodocstring.parser import parse_file
    from autodocstring.confidence.scorer import ConfidenceScorer

    manager = get_session_manager()
    session = manager.create_session()
    style = _normalize_style(style)
    
    from autodocstring.session.session_manager import _SESSIONS_DIR
    
    # Securely save uploaded files into the session workspace
    upload_dir = _SESSIONS_DIR / session.session_id / "workspace"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    saved_files: List[Path] = []
    
    for upload in files:
        if not upload.filename or not upload.filename.endswith(".py"):
            continue
            
        # Sanitize path to prevent directory traversal
        safe_rel_path = upload.filename.lstrip("/\\").replace("..", "")
        dest_path = (PROJECT_ROOT / upload_dir / safe_rel_path).resolve()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = await upload.read()
        dest_path.write_bytes(content)
        saved_files.append(dest_path)
        
    if not saved_files:
        # Cleanup empty session
        raise HTTPException(status_code=400, detail="No Python files found in upload")

    scorer = ConfidenceScorer()
    results: List[DocstringResultSchema] = []
    file_hashes: Dict[str, str] = {}

    for f in saved_files:
        fstr = str(f)
        file_hashes[fstr] = compute_file_hash(fstr)
        try:
            metadata = parse_file(fstr)
        except Exception:
            continue

        for func in metadata.functions:
            scoring = scorer.score(func)
            is_ok, reason = _docstring_status(func.docstring or "", func, style)
            results.append(DocstringResultSchema(
                file=fstr,
                function=func.name,
                lineno=func.lineno,
                docstring=func.docstring or "",
                confidence=round(scoring.confidence, 4),
                risk=scoring.risk.value if hasattr(scoring.risk, 'value') else scoring.risk,
                reason=scoring.reason,
                skipped=is_ok,
                skip_reason=reason,
                signature=_build_signature(func),
            ))
        for cls in metadata.classes:
            for method in cls.methods:
                scoring = scorer.score(method)
                is_ok, reason = _docstring_status(method.docstring or "", method, style)
                results.append(DocstringResultSchema(
                    file=fstr,
                    function=f"{cls.name}.{method.name}",
                    lineno=method.lineno,
                    docstring=method.docstring or "",
                    confidence=round(scoring.confidence, 4),
                    risk=scoring.risk.value if hasattr(scoring.risk, 'value') else scoring.risk,
                    reason=scoring.reason,
                    skipped=is_ok,
                    skip_reason=reason,
                    signature=_build_signature(method),
                ))

    if len(results) > MAX_FUNCTIONS_PER_REQUEST:
        return ScanResponse(session_id="", functions=[], error="scan_too_large")

    results.sort(key=lambda r: (r.file, r.lineno))
    manager.attach_scan_results(
        session,
        [r.model_dump() for r in results],
        file_hashes=file_hashes,
        docstring_style=style,
    )

    return ScanResponse(session_id=session.session_id, functions=results, session_dir=str(upload_dir))

# ---------------------------------------------------------------------------
# GET /api/v1/download/{session_id}
# ---------------------------------------------------------------------------

@router.get("/download/{session_id}", summary="Download a zip of the session's generated files")
def download_session_zip(session_id: str):
    from fastapi.responses import FileResponse
    import shutil
    from autodocstring.session.session_manager import _SESSIONS_DIR
    from autodocstring.safety.applier import _insert_docstrings
    from autodocstring.models.metadata import DocstringResult
    import tempfile
    import os
    
    manager = get_session_manager()
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    upload_dir = _SESSIONS_DIR / session.session_id / "workspace"
    if not upload_dir.exists():
        raise HTTPException(status_code=404, detail="Session workspace not found")
        
    # Create a temporary directory to store files with injected docstrings
    # This ensures we don't modify the original workspace files directly
    with tempfile.TemporaryDirectory() as temp_output_dir:
        temp_output_path = Path(temp_output_dir)

        # Iterate through all files in the session's workspace
        for original_file_path in upload_dir.rglob("*.py"): # Use rglob to find all .py files recursively
            if not original_file_path.is_file():
                continue

            relative_path = original_file_path.relative_to(upload_dir)
            destination_file_path = temp_output_path / relative_path
            destination_file_path.parent.mkdir(parents=True, exist_ok=True)

            original_source = original_file_path.read_text(encoding="utf-8")

            # Filter session results for this file
            # Try exact match first (case-insensitive for Windows), then filename-only fallback
            original_file_path_lower = str(original_file_path).lower()
            file_results_dict = [r for r in session.scan_results if r['file'].lower() == original_file_path_lower]
            if not file_results_dict:
                # Fallback: match on filename only (handles absolute path differences)
                fname = original_file_path.name.lower()
                file_results_dict = [r for r in session.scan_results if Path(r['file']).name.lower() == fname]
            
            if not file_results_dict:
                # If no docstrings for this file, just copy it as is
                destination_file_path.write_text(original_source, encoding="utf-8")
                continue

            # Convert to internal DocstringResult models for the applier
            results_for_file = [
                DocstringResult(
                    file=r["file"],
                    function=r["function"],
                    lineno=r["lineno"],
                    docstring=r["docstring"],
                    skipped=r.get("skipped", False),
                    skip_reason=r.get("skip_reason", "")
                )
                for r in file_results_dict
            ]
            
            # Inject docstrings
            new_source, _, _ = _insert_docstrings(original_source, results_for_file)
            
            # Write the modified content to the temporary directory
            destination_file_path.write_text(new_source, encoding="utf-8")

        # Create the zip archive from the temporary directory
        zip_base_name = _SESSIONS_DIR / session.session_id / f"project_{session_id}"
        shutil.make_archive(str(zip_base_name), 'zip', temp_output_path)
        
        # The FileResponse will handle sending the file and FastAPI's lifespan will handle temp_output_dir cleanup
        return FileResponse(
            path=str(zip_base_name) + ".zip",
            filename=f"documented_project_{session_id}.zip",
            media_type="application/zip"
        )

@router.post("/scan", response_model=ScanResponse, summary="Scan files and create a review session")
def scan(request: ScanRequest) -> ScanResponse:
    from autodocstring.utils.files import find_python_files
    from autodocstring.parser import parse_file
    from autodocstring.confidence.scorer import ConfidenceScorer

    safe_path = _resolve_safe_path(request.path)
    include = request.include or ["**/*.py"]
    exclude = request.exclude or ["tests/**", "**/__pycache__/**"]

    style = _normalize_style(request.style)
    files: List[Path] = (
        [safe_path] if safe_path.is_file()
        else list(find_python_files(str(safe_path), include, exclude))
    )

    scorer = ConfidenceScorer()
    results: List[DocstringResultSchema] = []
    file_hashes: Dict[str, str] = {}

    for f in files:
        fstr = str(f)
        file_hashes[fstr] = compute_file_hash(fstr)
        try:
            metadata = parse_file(fstr)
        except Exception:
            continue

        for func in metadata.functions:
            scoring = scorer.score(func)
            is_ok, reason = _docstring_status(func.docstring or "", func, style)
            results.append(DocstringResultSchema(
                file=fstr,
                function=func.name,
                lineno=func.lineno,
                docstring=func.docstring or "",
                confidence=round(scoring.confidence, 4),
                risk=scoring.risk.value if hasattr(scoring.risk, 'value') else scoring.risk,
                reason=scoring.reason,
                skipped=is_ok,
                skip_reason=reason,
                signature=_build_signature(func),
            ))
        for cls in metadata.classes:
            for method in cls.methods:
                scoring = scorer.score(method)
                is_ok, reason = _docstring_status(method.docstring or "", method, style)
                results.append(DocstringResultSchema(
                    file=fstr,
                    function=f"{cls.name}.{method.name}",
                    lineno=method.lineno,
                    docstring=method.docstring or "",
                    confidence=round(scoring.confidence, 4),
                    risk=scoring.risk.value if hasattr(scoring.risk, 'value') else scoring.risk,
                    reason=scoring.reason,
                    skipped=is_ok,
                    skip_reason=reason,
                    signature=_build_signature(method),
                ))

    if len(results) > MAX_FUNCTIONS_PER_REQUEST:
        return ScanResponse(session_id="", functions=[], error="scan_too_large")

    results.sort(key=lambda r: (r.file, r.lineno))

    manager = get_session_manager()
    session = manager.create_session()
    manager.attach_scan_results(
        session,
        [r.model_dump() for r in results],
        file_hashes=file_hashes,
        docstring_style=style,
    )

    return ScanResponse(session_id=session.session_id, functions=results)

# ---------------------------------------------------------------------------
# POST /api/v1/rescan
# ---------------------------------------------------------------------------

@router.post("/rescan", response_model=ScanResponse, summary="Rescan session with selected docstring style")
def rescan(request: RescanRequest) -> ScanResponse:
    from autodocstring.parser import parse_file
    from autodocstring.confidence.scorer import ConfidenceScorer
    from autodocstring.session.session_manager import _SESSIONS_DIR

    manager = get_session_manager()
    session = manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    style = _normalize_style(request.style)
    scorer = ConfidenceScorer()
    results: List[DocstringResultSchema] = []

    for fstr in session.file_hashes.keys():
        p = Path(fstr)
        if not p.exists():
            continue
        try:
            metadata = parse_file(str(p))
        except Exception:
            continue

        for func in metadata.functions:
            scoring = scorer.score(func)
            is_ok, reason = _docstring_status(func.docstring or "", func, style)
            results.append(DocstringResultSchema(
                file=fstr,
                function=func.name,
                lineno=func.lineno,
                docstring=func.docstring or "",
                confidence=round(scoring.confidence, 4),
                risk=scoring.risk.value if hasattr(scoring.risk, 'value') else scoring.risk,
                reason=scoring.reason,
                skipped=is_ok,
                skip_reason=reason,
                signature=_build_signature(func),
            ))
        for cls in metadata.classes:
            for method in cls.methods:
                scoring = scorer.score(method)
                is_ok, reason = _docstring_status(method.docstring or "", method, style)
                results.append(DocstringResultSchema(
                    file=fstr,
                    function=f"{cls.name}.{method.name}",
                    lineno=method.lineno,
                    docstring=method.docstring or "",
                    confidence=round(scoring.confidence, 4),
                    risk=scoring.risk.value if hasattr(scoring.risk, 'value') else scoring.risk,
                    reason=scoring.reason,
                    skipped=is_ok,
                    skip_reason=reason,
                    signature=_build_signature(method),
                ))

    results.sort(key=lambda r: (r.file, r.lineno))
    manager.attach_scan_results(
        session,
        [r.model_dump() for r in results],
        docstring_style=style,
    )

    session_dir = str(_SESSIONS_DIR / session.session_id / "workspace")
    return ScanResponse(session_id=session.session_id, functions=results, session_dir=session_dir)

# ---------------------------------------------------------------------------
# GET /api/v1/file
# ---------------------------------------------------------------------------

@router.get("/file", summary="Get source code of a scanned file")
def get_file_content(path: str, session_id: str) -> dict:
    manager = get_session_manager()
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    resolved = _resolve_safe_path(path)
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    # Verify file is part of the session
    # Do case-insensitive match for Windows just in case
    resolved_lower = str(resolved).lower()
    found_key = None
    for k in session.file_hashes.keys():
        if k.lower() == resolved_lower:
            found_key = k
            break
            
    if not found_key:
        raise HTTPException(status_code=403, detail="File not part of current session")
    else:
        # standardise on the key used in the session to avoid downstream issues
        resolved = Path(found_key)
        
    snapshot_path = session.get_snapshot_path(str(resolved))
    if snapshot_path.exists():
        resolved = snapshot_path

    return {
        "file": str(resolved),
        "content": resolved.read_text(encoding="utf-8")
    }

# ---------------------------------------------------------------------------
# POST /api/v1/preview
# ---------------------------------------------------------------------------

class PreviewRequest(BaseModel):
    session_id: str
    file_path: str

@router.post("/preview", summary="Get generated full-file preview string")
def preview_file(request: PreviewRequest) -> dict:
    from autodocstring.safety.applier import _insert_docstrings
    from autodocstring.models.metadata import DocstringResult
    
    manager = get_session_manager()
    session = manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    resolved = _resolve_safe_path(request.file_path)
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="File not found")

    original_source = resolved.read_text(encoding="utf-8")
    
    # Filter session results for this file only using case-insensitive match for Windows
    resolved_lower = str(resolved).lower()
    file_results_dict = [r for r in session.scan_results if r['file'].lower() == resolved_lower]
    
    if not file_results_dict:
        return {"file": str(resolved), "content": original_source}

    # Convert to internal DocstringResult models for the applier
    # schemas.py DocstringResultSchema matches models.metadata.DocstringResult reasonably close
    results = [
        DocstringResult(
            file=r["file"],
            function=r["function"],
            lineno=r["lineno"],
            docstring=r["docstring"],
            skipped=r.get("skipped", False),
            skip_reason=r.get("skip_reason", "")
        )
        for r in file_results_dict
    ]
    
    new_source, _, _ = _insert_docstrings(original_source, results)
    return {
        "file": str(resolved),
        "content": new_source
    }

# ---------------------------------------------------------------------------
# POST /api/v1/save_file
# ---------------------------------------------------------------------------

class SaveFileRequest(BaseModel):
    session_id: str
    file_path: str
    content: str

@router.post("/save_file", summary="Blindly save user-edited text to a file")
def save_file(request: SaveFileRequest) -> dict:
    manager = get_session_manager()
    session = manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    resolved = _resolve_safe_path(request.file_path)
    
    # Write directly. Since this bypasses AST safety (user explicitly typed it), we just write it.
    resolved.write_text(request.content, encoding="utf-8")
    
    return {"success": True, "file": str(resolved)}

# ---------------------------------------------------------------------------
# POST /api/v1/generate
# ---------------------------------------------------------------------------

def _merge_and_save_results(manager, session, new_results: List[DocstringResultSchema]) -> List[dict]:
    new_map = {f"{r.file}::{r.function}::{r.lineno}": r for r in new_results}
    merged = []
    # If a result is completely missing from existing scan_results but was generated, it won't be in old_r.
    # To be perfectly safe, we'll keep all old, and just overwrite matching ones.
    for old_r in session.scan_results:
        key = f"{old_r['file']}::{old_r['function']}::{old_r['lineno']}"
        if key in new_map:
            merged.append(new_map[key].model_dump())
            del new_map[key]
        else:
            merged.append(old_r)
    # Add any totally new ones that weren't in scan_results
    for r in new_map.values():
        merged.append(r.model_dump())
    
    merged.sort(key=lambda r: (r['file'], r['lineno']))
    manager.attach_scan_results(session, merged)
    return merged

def _run_engine_for_files(session_id: str, files: List[str], request: GenerateRequest, target_func_id: str = None) -> List[DocstringResultSchema]:
    from autodocstring.generator.engine import HybridDocstringEngine
    from autodocstring.parser import parse_file
    from autodocstring.validation.validator import DocstringValidator
    import uuid
    import shutil
    from autodocstring.session.session_manager import _SESSIONS_DIR

    manager = get_session_manager()
    session = manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    # Create batch snapshot
    batch_id = str(uuid.uuid4())
    session.current_batch_id = batch_id
    session.is_cancelled = False
    
    snapshot_dir = _SESSIONS_DIR / batch_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    for fpath in session.file_hashes.keys():
        src = Path(fpath)
        if src.exists():
            dest = session.get_snapshot_path(fpath)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dest))

    provider = _build_provider(request.llm_provider or "none")
    style = _normalize_style(request.style)
    manager.set_docstring_style(session, style)
    engine = HybridDocstringEngine(
        style=style,
        provider=provider,
        confidence_threshold=request.confidence_threshold or REVIEW,
        rewrite_existing=request.rewrite_existing or False,
    )

    # Validator: runs after generation, applies auto-fixes
    validator = DocstringValidator(autofix=True, use_pydocstyle=False)

    all_results: List[DocstringResultSchema] = []
    for filepath in files:
        # Check cancellation
        session = manager.get_session(session_id)
        if session and session.is_cancelled:
            break
            
        p = session.get_snapshot_path(filepath)
        if not p.exists():
            continue
        try:
            metadata = parse_file(str(p))
        except Exception:
            continue
            
        source_lines = p.read_text(encoding="utf-8").splitlines()
        results = engine.generate_for_module(metadata, filepath=filepath, source_lines=source_lines)
        
        for r in results:
            fid = f"{r.file}::{r.function}::{r.lineno}"
            if target_func_id and fid != target_func_id:
                continue

            # ── Post-generation validation + auto-fix ─────────────────
            is_new = getattr(r, "generation_type", "") != "existing"
            if r.docstring and not r.skipped and is_new:
                context = {"name": r.function, "type": "function"}
                issues = validator.validate_docstring(r.docstring, context)
                if issues:
                    print(
                        f"[Validator] {r.function} @ {r.file}:{r.lineno} — "
                        + ", ".join(str(i) for i in issues)
                    )
                # Apply auto-fixes (e.g. missing period, spacing)
                r.docstring = validator.fix_docstring(r.docstring)
            # ──────────────────────────────────────────────────────────

            all_results.append(_result_to_schema(r))
            
        # Optional: Save session mid-way so frontend sees progress
        _merge_and_save_results(manager, session, all_results)
            
    return all_results

@router.post("/generate", response_model=List[DocstringResultSchema], summary="Generate docstring for a specific function")
def generate_function(request: GenerateRequest) -> List[DocstringResultSchema]:
    manager = get_session_manager()
    session = manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not request.function_id:
        files = list({r["file"] for r in session.scan_results})
        return _run_engine_for_files(request.session_id, files, request)

    try:
        file_path = request.function_id.split("::")[0]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid function_id format")

    return _run_engine_for_files(request.session_id, [file_path], request, target_func_id=request.function_id)

@router.post("/generate/file", response_model=List[DocstringResultSchema], summary="Generate docstrings for a specific file")
def generate_file(request: GenerateRequest) -> List[DocstringResultSchema]:
    if not request.file:
        raise HTTPException(status_code=400, detail="file is required")
    return _run_engine_for_files(request.session_id, [request.file], request)


@router.post("/generate/cancel", summary="Cancel ongoing bulk generation")
def cancel_generation(request: GenerateRequest) -> dict:
    manager = get_session_manager()
    session = manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.is_cancelled = True
    manager.save_session(session)
    return {"status": "cancelled"}

class GenerationSummary(BaseModel):
    """Response for generate/all including validation quality score."""
    results: List[DocstringResultSchema]
    quality_score: int   # 0–100 across all generated docstrings
    total_generated: int
    warnings: int
    errors: int


@router.post("/generate/all", response_model=GenerationSummary, summary="Generate docstrings for all files in session")
def generate_all(request: GenerateRequest) -> GenerationSummary:
    manager = get_session_manager()
    session = manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    files = list({r["file"] for r in session.scan_results})
    results = _run_engine_for_files(request.session_id, files, request)

    # ── Aggregate validation quality score ───────────────────────────
    from autodocstring.validation.validator import DocstringValidator
    validator = DocstringValidator(autofix=False, use_pydocstyle=False)
    
    total_errors = 0
    total_warnings = 0
    generated_count = 0

    for r in results:
        if r.skipped or not r.docstring or getattr(r, "generation_type", "") == "existing":
            continue
        generated_count += 1
        context = {"name": r.function, "type": "function"}
        issues = validator.validate_docstring(r.docstring, context)
        for issue in issues:
            if issue.severity.value == "error":
                total_errors += 1
            else:
                total_warnings += 1

    # Score: start at 100, penalise per issue
    raw_penalty = (total_errors * 20) + (total_warnings * 5)
    quality_score = max(0, 100 - raw_penalty) if generated_count > 0 else 100
    # ─────────────────────────────────────────────────────────────────

    return GenerationSummary(
        results=results,
        quality_score=quality_score,
        total_generated=generated_count,
        warnings=total_warnings,
        errors=total_errors,
    )

# ---------------------------------------------------------------------------
# POST /api/v1/review
# ---------------------------------------------------------------------------

@router.post("/review", summary="Record reviewer decisions in session")
def review(request: ReviewRequest) -> dict:
    manager = get_session_manager()
    session = manager.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {request.session_id}")

    decisions = [d.model_dump() for d in request.decisions]
    recorded = manager.update_decisions(session, decisions)
    approved = sum(1 for d in request.decisions if d.approved)
    rejected = len(request.decisions) - approved

    return {
        "session_id": request.session_id,
        "recorded": recorded,
        "approved": approved,
        "rejected": rejected,
        "total": len(request.decisions),
    }

# ---------------------------------------------------------------------------
# POST /api/v1/apply
# ---------------------------------------------------------------------------

@router.post("/apply", summary="Apply approved docstrings from session to files")
async def apply_docstrings(request: ApplyRequest) -> dict:
    from autodocstring.generator.engine import HybridDocstringEngine
    from autodocstring.parser import parse_file
    from autodocstring.safety.transaction import run_atomic_apply

    manager = get_session_manager()
    session = manager.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {request.session_id}")

    approved = session.approved_decisions()
    if not approved:
        return {
            "session_id": request.session_id,
            "success": True,
            "applied": 0,
            "skipped": 0,
            "message": "No approved decisions in session",
            "files": [],
            "error": "",
            "restored_files": [],
        }

    by_file_decisions: Dict[str, list] = {}
    for d in approved:
        by_file_decisions.setdefault(d.file, []).append(d)

    if not request.dry_run:
        for filepath in by_file_decisions:
            if session.check_file_conflict(filepath):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "file_modified_since_review",
                        "file": filepath,
                        "action": "please rescan",
                    },
                )

    engine = HybridDocstringEngine()
    file_results: Dict[str, list] = {}

    for filepath, decisions in sorted(by_file_decisions.items()):
        p = Path(filepath)
        if not p.exists():
            file_results[filepath] = []
            continue

        lock = await _get_file_lock(filepath)
        async with lock:
            try:
                metadata = parse_file(filepath)
                source_lines = p.read_text(encoding="utf-8").splitlines()
                all_gen = engine.generate_for_module(
                    metadata, filepath=filepath, source_lines=source_lines
                )
                approved_linenos = {d.lineno for d in decisions}
                file_results[filepath] = [
                    r for r in all_gen
                    if r.lineno in approved_linenos and not r.skipped
                ]
            except Exception:
                file_results[filepath] = []
            finally:
                _release_file_lock(filepath)

    tx = run_atomic_apply(
        session_id=request.session_id,
        by_file=file_results,
        dry_run=request.dry_run or False,
        keep_backup=(not request.dry_run),
    )

    return {
        "session_id": request.session_id,
        "success": tx.success,
        "applied": tx.applied,
        "skipped": tx.skipped,
        "files": [
            {
                "file": fr.file,
                "applied": fr.applied,
                "skipped": fr.skipped,
                "rolled_back": fr.rolled_back,
                "error": fr.error,
            }
            for fr in tx.files
        ],
        "error": tx.error if not tx.success else "",
        "restored_files": tx.restored_files,
    }

# ---------------------------------------------------------------------------
# POST /api/v1/undo
# ---------------------------------------------------------------------------

@router.post("/undo", response_model=UndoResponse, summary="Undo applied docstrings by restoring files from backup")
def undo_docstrings(request: UndoRequest) -> UndoResponse:
    from autodocstring.safety.transaction import restore_session_backup
    manager = get_session_manager()
    session = manager.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {request.session_id}")

    restored = restore_session_backup(request.session_id)
    
    return UndoResponse(
        success=bool(restored),
        restored_files=restored,
        error=None if restored else "No backup found or no files restored",
    )

# ---------------------------------------------------------------------------
# GET /api/v1/session/{session_id}
# ---------------------------------------------------------------------------

@router.get("/session/{session_id}", response_model=SessionResponse, summary="Get session state")
def get_session(session_id: str) -> SessionResponse:
    manager = get_session_manager()
    session = manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return SessionResponse(session_id=session.session_id, functions=session.scan_results)

# ---------------------------------------------------------------------------
# GET /api/v1/diff
# ---------------------------------------------------------------------------

@router.get("/diff", summary="Get unified diff for session decisions")
def get_diff(session_id: str) -> dict:
    from autodocstring.safety.applier import SafeApplier
    from autodocstring.models.metadata import DocstringResult

    manager = get_session_manager()
    session = manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    approved = session.approved_decisions()
    if not approved:
        return {"session_id": session_id, "diff": "", "files": []}

    approved_by_file: Dict[str, set] = {}
    for d in approved:
        approved_by_file.setdefault(d.file, set()).add(d.lineno)

    applier = SafeApplier(dry_run=True)
    combined_diff = ""
    file_diffs = []

    for filepath, linenos in sorted(approved_by_file.items()):
        p = Path(filepath)
        if not p.exists():
            continue
        
        results_for_file = []
        for r in session.scan_results:
            if r["file"] == filepath and r["lineno"] in linenos and r["docstring"]:
                results_for_file.append(
                    DocstringResult(
                        file=filepath,
                        function=r["function"],
                        lineno=r["lineno"],
                        docstring=r["docstring"],
                        confidence=r["confidence"],
                    )
                )
        
        if not results_for_file:
            continue

        results_for_file.sort(key=lambda x: x.lineno)
        try:
            ar = applier.apply_to_file(filepath, results_for_file)
            if ar.diff:
                combined_diff += ar.diff + "\n"
                file_diffs.append({"file": filepath, "diff": ar.diff})
        except Exception:
            pass

    return {"session_id": session_id, "diff": combined_diff, "files": file_diffs}

# ---------------------------------------------------------------------------
# GET /api/v1/coverage
# ---------------------------------------------------------------------------

@router.get("/coverage", response_model=ExpandedCoverageStats, summary="Get expanded documentation coverage")
def get_coverage(
    path: str,
    threshold: float = 80.0,
    session_id: Optional[str] = None,
    style: Optional[str] = None,
) -> ExpandedCoverageStats:
    from autodocstring.utils.files import find_python_files
    from autodocstring.parser import parse_file

    safe_path = _resolve_safe_path(path)
    files: List[Path] = (
        [safe_path] if safe_path.is_file()
        else list(find_python_files(str(safe_path), ["**/*.py"], ["tests/**", "**/__pycache__/**"]))
    )

    manager = get_session_manager()
    session = manager.get_session(session_id) if session_id else None
    requested_style = _normalize_style(style or (session.docstring_style if session else None))

    total_funcs = 0
    already_documented = 0

    for f in files:
        try:
            metadata = parse_file(str(f))
        except Exception:
            continue
            
        for func in metadata.get_all_functions():
            total_funcs += 1
            is_ok, _ = _docstring_status(func.docstring or "", func, requested_style)
            if is_ok:
                already_documented += 1

    added = 0
    improved = 0

    if session:
        for r in session.scan_results:
            # If generation_type is existing, it was unmodified. We only count actual generations.
            gen_type = r.get("generation_type", "")
            if gen_type not in ("skipped", "existing", "none", ""):
                if r.get("reason") == "improve suggestion":
                    improved += 1
                else:
                    added += 1

    coverage_before = round((already_documented / total_funcs * 100) if total_funcs else 100, 2)
    coverage_after = round(((already_documented + added) / total_funcs * 100) if total_funcs else 100, 2)

    automation_safe_percent = coverage_before
    requires_review_percent = round(100.0 - automation_safe_percent, 2)
    unsafe_skipped_percent = 0.0
    estimated_new_docstrings = max(total_funcs - already_documented, 0)

    return ExpandedCoverageStats(
        coverage_before=coverage_before,
        coverage_after=coverage_after,
        added=added,
        improved=improved,
        total_functions=total_funcs,
        total_files=len(files),
        documentation_coverage_before=coverage_before,
        documentation_coverage_after=coverage_after,
        automation_safe_percent=automation_safe_percent,
        requires_review_percent=requires_review_percent,
        unsafe_skipped_percent=unsafe_skipped_percent,
        estimated_new_docstrings=estimated_new_docstrings,
        unchanged_existing=already_documented,
        skipped_existing=0,
    )

@router.get("/health", summary="Basic health check")
def health() -> dict:
    uptime = int((datetime.utcnow() - _start_time).total_seconds())
    manager = get_session_manager()
    return {
        "status": "ok",
        "llm_available": False,
        "active_sessions": manager.active_count(),
        "project_root": str(PROJECT_ROOT),
        "uptime_seconds": uptime,
        "version": _API_VERSION,
    }

@app.post("/scan", include_in_schema=False)
@app.get("/scan", include_in_schema=False)
def _deprecated_scan():
    raise HTTPException(status_code=410, detail="Endpoint moved to /api/v1/scan")

@app.post("/generate", include_in_schema=False)
@app.get("/generate", include_in_schema=False)
def _deprecated_generate():
    raise HTTPException(status_code=410, detail="Endpoint moved to /api/v1/generate")

@app.post("/review", include_in_schema=False)
@app.get("/review", include_in_schema=False)
def _deprecated_review():
    raise HTTPException(status_code=410, detail="Endpoint moved to /api/v1/review")

@app.post("/apply", include_in_schema=False)
@app.get("/apply", include_in_schema=False)
def _deprecated_apply():
    raise HTTPException(status_code=410, detail="Endpoint moved to /api/v1/apply")

@app.post("/diff", include_in_schema=False)
@app.get("/diff", include_in_schema=False)
def _deprecated_diff():
    raise HTTPException(status_code=410, detail="Endpoint moved to /api/v1/diff")

@app.post("/coverage", include_in_schema=False)
@app.get("/coverage", include_in_schema=False)
def _deprecated_coverage():
    raise HTTPException(status_code=410, detail="Endpoint moved to /api/v1/coverage")

@app.get("/health", include_in_schema=False)
def _deprecated_health():
    raise HTTPException(status_code=410, detail="Endpoint moved to /api/v1/health")

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.getenv("PORT", "8001"))
    uvicorn.run("autodocstring.api.app:app", host="0.0.0.0", port=PORT, reload=False)
