"""Groq LLM provider for docstring summary generation.

Uses the Groq OpenAI-compatible endpoint to generate a single-sentence
summary for a Python function.  Only the summary sentence is generated —
the Args / Returns / Raises sections are always built by the deterministic
template layer.

Activation:
    Set the ``GROQ_API_KEY`` environment variable.  If the key is absent
    the provider raises ``RuntimeError`` at construction time so the
    caller can fall back gracefully.

Optional overrides (environment variables):
    GROQ_API_KEY   — required; Bearer token for the Groq API
    LLM_MODEL      — override the default model (default: llama3-70b-8192)
"""
import os
from typing import Any, Dict, Optional

import httpx


_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_DEFAULT_MODEL = "llama-3.3-70b-versatile"
_TIMEOUT = 45.0

_SYSTEM_PROMPT = (
    "You are a Python documentation assistant. "
    "Write concise, accurate single-sentence docstring summaries. "
    "Return ONLY the summary sentence — no quotes, no section headers, no explanation."
)


class GroqProvider:
    """LLM provider that calls the Groq API to generate docstring summaries.

    Only the one-line summary sentence is generated via the LLM.
    Structured sections (Args, Returns, Raises) are rendered by the
    deterministic template engine and are never passed to the LLM,
    preventing hallucination of parameter names or types.

    Attributes:
        model: Groq model identifier to use for generation.
        api_key: Groq API Bearer token read from ``GROQ_API_KEY`` env var.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        timeout: float = _TIMEOUT,
    ):
        """Initialise the Groq provider.

        Args:
            model: Model name to request from Groq.  Defaults to the value
                of the ``LLM_MODEL`` environment variable, or
                ``llama3-70b-8192`` if neither is set.
            timeout: HTTP request timeout in seconds.  Defaults to 45.

        Raises:
            RuntimeError: If ``GROQ_API_KEY`` is not set in the environment.
        """
        self.api_key = os.getenv("GROQ_API_KEY", "")
        if not self.api_key:
            raise RuntimeError(
                "GROQ_API_KEY environment variable is not set. "
                "Groq provider cannot be used without an API key."
            )
        self.model = model or os.getenv("LLM_MODEL", _DEFAULT_MODEL)
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Summary generation
    # ------------------------------------------------------------------

    def generate_summary(self, metadata: Dict[str, Any]) -> Optional[str]:
        """Generate a concise summary sentence for a Python function.

        Sends the function name, parameters, and return type to the Groq
        API and returns a single-sentence summary.  Only the summary is
        generated — structured docstring sections are handled by the
        template engine.

        Args:
            metadata: Dictionary with keys ``name`` (str), ``params``
                (list of str), and ``return_type`` (str).

        Returns:
            A single-sentence summary string, or ``None`` if generation
            fails for any reason (network error, API error, empty response).
        """
        param_str = ", ".join(metadata.get("params", [])) or "none"
        raises_list = metadata.get("raises", [])
        body_snippet = metadata.get("body_snippet")

        body_section = ""
        if body_snippet:
            body_section = f"Function body (first few lines):\n{body_snippet}\n\n"

        raises_rule = (
            "- Do NOT mention raising exceptions, errors, or validation failures "
            "— this function does not raise any exceptions."
            if not raises_list
            else f"- This function raises: {', '.join(raises_list)}."
        )

        user_prompt = (
            f"Write a concise, single-sentence docstring summary for a Python "
            f"function named `{metadata['name']}`.\n"
            f"Parameters: {param_str}\n"
            f"Returns: {metadata.get('return_type', 'None')}\n\n"
            f"{body_section}"
            "Rules:\n"
            "- Return ONLY the summary sentence (max 15 words).\n"
            "- Do not include quotes, 'Args:', 'Returns:', or section headers.\n"
            "- Start with a verb (e.g. Calculates, Fetches, Validates, Checks).\n"
            "- Be specific to what the function actually does based on its body.\n"
            f"{raises_rule}"
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(_GROQ_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                summary = (
                    response.json()["choices"][0]["message"]["content"].strip()
                )

                # Strip surrounding quotes if the model adds them
                if (
                    len(summary) >= 2
                    and summary[0] in ('"', "'")
                    and summary[-1] == summary[0]
                ):
                    summary = summary[1:-1].strip()

                # Take only the first sentence
                import re
                summary = re.sub(
                    r'^(here is a[^:]*:|docstring:|summary:)\s*',
                    '',
                    summary,
                    flags=re.IGNORECASE,
                ).strip()
                for ch in (".", "\n"):
                    idx = summary.find(ch)
                    if idx != -1 and idx > 10:
                        summary = summary[: idx + 1]
                        break

                # Reject summaries that are too short to be meaningful
                if len(summary) < 8:
                    return None

                return summary

        except Exception as e:
            print(f"GroqProvider: Error calling Groq API — {e}")
            return None

    # ------------------------------------------------------------------
    # Structured generation (summary + params + returns)
    # ------------------------------------------------------------------

    def generate_docstring_parts(self, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate summary, parameter descriptions, and returns description as JSON.

        Asks Groq to return a structured JSON object so the engine can splice
        all three parts into the template-generated docstring.

        Args:
            metadata: Dictionary with keys ``name``, ``params``, ``return_type``,
                ``raises``, and optional ``body_snippet``.

        Returns:
            Dict with keys ``summary`` (str), ``params`` (dict[str, str]),
            ``returns`` (str | None), or ``None`` on failure.
        """
        import json as _json

        param_entries = metadata.get("params", [])   # ["name: type", ...]
        param_str = ", ".join(param_entries) or "none"
        param_names = [p.split(":")[0].strip() for p in param_entries]
        raises_list = metadata.get("raises", [])
        body_snippet = metadata.get("body_snippet")
        return_type = metadata.get("return_type", "None")

        body_section = ""
        if body_snippet:
            body_section = f"Function body (first few lines):\n{body_snippet}\n\n"

        raises_rule = (
            "- Do NOT mention raising, errors, or validation failures in any "
            "field — this function does not raise any exceptions."
            if not raises_list
            else f"- This function raises: {', '.join(raises_list)}."
        )

        # Build a small JSON example to anchor the format
        example_params = {n: "short description" for n in param_names[:3]}
        example_json = _json.dumps(
            {"summary": "Verb phrase describing what this does.",
             "params": example_params,
             "returns": "What is returned." if return_type != "None" else None},
            indent=None,
        )

        user_prompt = (
            f"Return a JSON object describing the Python function `{metadata['name']}`.\n"
            f"Parameters: {param_str}\n"
            f"Returns: {return_type}\n\n"
            f"{body_section}"
            "JSON keys required:\n"
            '  "summary"  — single sentence starting with a verb, max 15 words\n'
            '  "params"   — object mapping each parameter name to a specific 5-10 word description\n'
            '  "returns"  — specific 5-10 word description of the return value, '
            'or null if the function returns None\n\n'
            "Rules:\n"
            "- param descriptions MUST be specific (not 'The X parameter').\n"
            "- Base descriptions on the actual function body shown above.\n"
            f"{raises_rule}\n\n"
            f"Example format: {example_json}"
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(_GROQ_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                raw = response.json()["choices"][0]["message"]["content"].strip()
                data = _json.loads(raw)

                summary = data.get("summary", "")
                if isinstance(summary, str):
                    summary = summary.strip()
                    import re as _re
                    summary = _re.sub(
                        r'^(here is a[^:]*:|docstring:|summary:)\s*',
                        '', summary, flags=_re.IGNORECASE,
                    ).strip()
                    # Keep only first sentence
                    for ch in (".", "\n"):
                        idx = summary.find(ch)
                        if idx != -1 and idx > 10:
                            summary = summary[: idx + 1]
                            break
                    if len(summary) < 8:
                        summary = ""

                params_raw = data.get("params") or {}
                params_clean: Dict[str, str] = {}
                if isinstance(params_raw, dict):
                    for k, v in params_raw.items():
                        if isinstance(k, str) and isinstance(v, str) and v.strip():
                            params_clean[k] = v.strip()

                returns_raw = data.get("returns")
                returns_clean = None
                if isinstance(returns_raw, str) and returns_raw.strip():
                    returns_clean = returns_raw.strip()

                if not summary:
                    return None

                return {
                    "summary": summary,
                    "params": params_clean,
                    "returns": returns_clean,
                }

        except Exception as e:
            print(f"GroqProvider: Error in generate_docstring_parts — {e}")
            return None
