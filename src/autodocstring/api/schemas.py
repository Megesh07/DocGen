"""Pydantic schemas for FastAPI request/response bodies.

Phase 10 (API freeze): These schemas are the stable contract for the React UI.
Do not change response field names or types after this release.
"""
from typing import List, Optional
from pydantic import BaseModel


class ScanRequest(BaseModel):
    """Request body for POST /scan."""
    path: str
    include: Optional[List[str]] = None
    exclude: Optional[List[str]] = None
    style: Optional[str] = "google"


class GenerateRequest(BaseModel):
    """Request body for POST /generate."""
    session_id: str
    style: Optional[str] = "google"
    llm_provider: Optional[str] = "none"
    confidence_threshold: Optional[float] = 0.60
    rewrite_existing: Optional[bool] = False
    function_id: Optional[str] = None
    file: Optional[str] = None


class RescanRequest(BaseModel):
    """Request body for POST /rescan."""
    session_id: str
    style: Optional[str] = "google"


class FunctionDecision(BaseModel):
    """A reviewer's decision for one function."""
    file: str
    function: str
    lineno: int = 0
    approved: bool


class ReviewRequest(BaseModel):
    """Request body for POST /review."""
    session_id: str
    decisions: List[FunctionDecision]


class ApplyRequest(BaseModel):
    """Request body for POST /apply."""
    session_id: str
    dry_run: Optional[bool] = False


class DocstringResultSchema(BaseModel):
    """Serializable response for one function's docstring result."""
    file: str
    function: str
    lineno: int
    docstring: str = ""
    confidence: float = 1.0
    risk: str = "LOW"
    reason: str = ""
    diff: str = ""
    skipped: bool = False
    skip_reason: str = ""
    generation_type: str = "none"
    # Human-readable signature string: "func(a: int, b: str) -> bool"
    # Used by the frontend to compute missingParams / missingReturns metrics.
    signature: str = ""


class ScanResponse(BaseModel):
    """Response for POST /scan.

    On success: session_id is a UUID, functions is a sorted list.
    On scan_too_large error: session_id is empty, error field is set.
    """
    session_id: str
    functions: List[DocstringResultSchema]
    session_dir: Optional[str] = None
    error: Optional[str] = None
    suggested_action: Optional[str] = None


class ExpandedCoverageStats(BaseModel):
    """Expanded coverage statistics response (Phase 7).

    Attributes:
        coverage_before: % documented before generation.
        coverage_after: % after applying all auto-safe results.
        added: Number of newly added docstrings.
        improved: Number of improved existing docstrings.
        total_functions: Total functions found.
        total_files: Total files scanned.

        documentation_coverage_before/after and automation_* fields are
        legacy keys retained for API compatibility.
    """
    coverage_before: float
    coverage_after: float
    added: int
    improved: int
    total_functions: int
    total_files: int

    documentation_coverage_before: float
    documentation_coverage_after: float
    automation_safe_percent: float
    requires_review_percent: float
    unsafe_skipped_percent: float
    estimated_new_docstrings: int
    unchanged_existing: int
    skipped_existing: int


class UndoRequest(BaseModel):
    """Request body for POST /undo."""
    session_id: str


class UndoResponse(BaseModel):
    """Response body for POST /undo."""
    success: bool
    restored_files: List[str]
    error: Optional[str] = None


class SessionResponse(BaseModel):
    """Response body for GET /session/{session_id}."""
    session_id: str
    functions: List[DocstringResultSchema]
