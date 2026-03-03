"""Configuration loader for autodocstring."""
from typing import Dict, List, Optional, Any
from pathlib import Path

# Fix #9: tomllib compatibility for Python 3.8–3.12
try:
    import tomllib  # stdlib >= 3.11
except ModuleNotFoundError:
    try:
        import tomllib  # type: ignore[no-redef]  # pip install tomllib
    except ModuleNotFoundError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]  # pip install tomli
        except ModuleNotFoundError:
            import toml as tomllib  # type: ignore[no-redef]  # legacy fallback


class Config:
    """Configuration for autodocstring tool.

    Attributes:
        style: Docstring style (google, numpy, rest).
        include: List of glob patterns to include.
        exclude: List of glob patterns to exclude.
        coverage_threshold: Minimum coverage percentage.
        output_format: Output format (terminal, csv, html, json).
        autofix: Enable automatic fixing.
        validate: Enable validation.
        confidence_threshold: Minimum confidence to generate (0–1).
        mode: Operating mode (report | review | enforce).
        llm_provider: LLM provider name (none | local).
        llm_base_url: Base URL for local LLM server.
        llm_model: Model name for local LLM.
        ignore_patterns: Glob patterns for files to ignore.
    """

    def __init__(
        self,
        style: str = "google",
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        coverage_threshold: float = 80.0,
        output_format: str = "terminal",
        autofix: bool = True,
        validate: bool = True,
        # New fields
        confidence_threshold: float = 0.60,
        mode: str = "review",
        llm_provider: str = "none",
        llm_base_url: str = "http://localhost:11434",
        llm_model: str = "mistral",
        ignore_patterns: Optional[List[str]] = None,
    ):
        """Initialize configuration.

        Args:
            style: Docstring style. Defaults to ``google``.
            include: Include patterns. Defaults to None.
            exclude: Exclude patterns. Defaults to None.
            coverage_threshold: Coverage threshold. Defaults to 80.0.
            output_format: Output format. Defaults to ``terminal``.
            autofix: Enable autofix. Defaults to True.
            validate: Enable validation. Defaults to True.
            confidence_threshold: Minimum confidence score to generate a
                docstring. Defaults to 0.60.
            mode: Operating mode. Defaults to ``review``.
            llm_provider: LLM provider name. Defaults to ``none``.
            llm_base_url: Base URL for local LLM server.
                Defaults to ``http://localhost:11434``.
            llm_model: Model name. Defaults to ``mistral``.
            ignore_patterns: Additional glob patterns to ignore.
                Defaults to None.
        """
        self.style = style
        self.include = include or ["**/*.py"]
        self.exclude = exclude or [
            "tests/**",
            "**/__pycache__/**",
            "**/venv/**",
            "**/.venv/**",
        ]
        self.coverage_threshold = coverage_threshold
        self.output_format = output_format
        self.autofix = autofix
        self.validate = validate
        # New fields
        self.confidence_threshold = confidence_threshold
        self.mode = mode
        self.llm_provider = llm_provider
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.ignore_patterns = ignore_patterns or []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create config from dictionary.

        Args:
            data: Configuration dictionary.

        Returns:
            Config instance.
        """
        return cls(
            style=data.get("style", "google"),
            include=data.get("include"),
            exclude=data.get("exclude"),
            coverage_threshold=data.get("coverage_threshold", 80.0),
            output_format=data.get("output_format", "terminal"),
            autofix=data.get("autofix", True),
            validate=data.get("validate", True),
            # New fields
            confidence_threshold=data.get("confidence_threshold", 0.60),
            mode=data.get("mode", "review"),
            llm_provider=data.get("llm_provider", "none"),
            llm_base_url=data.get("llm_base_url", "http://localhost:11434"),
            llm_model=data.get("llm_model", "mistral"),
            ignore_patterns=data.get("ignore_patterns"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary.

        Returns:
            Configuration dictionary.
        """
        return {
            "style": self.style,
            "include": self.include,
            "exclude": self.exclude,
            "coverage_threshold": self.coverage_threshold,
            "output_format": self.output_format,
            "autofix": self.autofix,
            "validate": self.validate,
            "confidence_threshold": self.confidence_threshold,
            "mode": self.mode,
            "llm_provider": self.llm_provider,
            "llm_base_url": self.llm_base_url,
            "llm_model": self.llm_model,
            "ignore_patterns": self.ignore_patterns,
        }


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from pyproject.toml.

    Args:
        config_path: Path to config file. Defaults to None (search for pyproject.toml).

    Returns:
        Config instance.
    """
    if config_path:
        config_file = Path(config_path)
    else:
        # Search for pyproject.toml in current directory and parents
        config_file = find_pyproject_toml()

    if config_file and config_file.exists():
        try:
            data = toml.load(config_file)
            tool_config = data.get("tool", {}).get("autodocstring", {})
            return Config.from_dict(tool_config)
        except Exception:
            # If loading fails, return default config
            pass

    return Config()


def find_pyproject_toml() -> Optional[Path]:
    """Find pyproject.toml in current directory or parents.

    Returns:
        Path to pyproject.toml if found, None otherwise.
    """
    current = Path.cwd()

    # Check current directory and up to 5 levels up
    for _ in range(5):
        pyproject = current / "pyproject.toml"
        if pyproject.exists():
            return pyproject

        parent = current.parent
        if parent == current:
            # Reached root
            break
        current = parent

    return None
