import os
import json
import httpx
import subprocess
import time
from typing import Dict, Any, Optional


class OllamaProvider:
    """LLM Provider for local Ollama instances running Llama 3.
    
    Handles automatic service startup if Ollama isn't already running.
    Uses the hybrid approach: AST-generated template → LLM enhances the summary only.
    This prevents hallucination by keeping the structured Args/Returns sections intact.
    """

    # Common Ollama binary paths on Windows
    _OLLAMA_PATHS = [
        r"C:\Users\{}\AppData\Local\Programs\Ollama\ollama.exe".format(os.environ.get("USERNAME", "")),
        r"C:\Program Files\Ollama\ollama.exe",
        "ollama",  # if in PATH
    ]

    def __init__(
        self,
        model_name: str = "llama3:latest",
        url: str = "http://127.0.0.1:11434/api/generate",
        timeout: float = 45.0,
        auto_start: bool = True,
    ):
        self.model_name = model_name
        self.url = url
        self.timeout = timeout

        if auto_start:
            self._ensure_running()

    # ------------------------------------------------------------------
    # Service management
    # ------------------------------------------------------------------

    def _ensure_running(self) -> None:
        """Check if Ollama is running; try to start it if not."""
        try:
            httpx.get("http://127.0.0.1:11434/api/tags", timeout=3.0)
            return  # already up
        except Exception:
            pass  # not running — try to start

        ollama_bin = None
        for path in self._OLLAMA_PATHS:
            if os.path.isfile(path):
                ollama_bin = path
                break
        
        if not ollama_bin:
            print("OllamaProvider: Ollama binary not found. Generation will fall back to template.")
            return

        try:
            subprocess.Popen(
                [ollama_bin, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            # Wait up to 8 seconds for it to start
            for _ in range(8):
                time.sleep(1)
                try:
                    httpx.get("http://127.0.0.1:11434/api/tags", timeout=2.0)
                    print("OllamaProvider: Started Ollama service automatically.")
                    return
                except Exception:
                    pass
        except Exception as e:
            print(f"OllamaProvider: Could not start Ollama: {e}")

    # ------------------------------------------------------------------
    # Summary generation
    # ------------------------------------------------------------------

    def generate_summary(self, metadata: Dict[str, Any]) -> Optional[str]:
        """Generate a concise summary sentence using Llama 3 for the given function metadata.
        
        This is called AFTER the AST template has already built the Args/Returns sections.
        Only the first-line summary is replaced by the LLM to make it more descriptive.
        This hybrid approach prevents hallucination.
        
        Args:
            metadata: Dictionary containing 'name', 'params', 'return_type', and 'raises'.
            
        Returns:
            A string containing the improved summary sentence, or None if LLM unavailable.
        """
        param_str = ", ".join(metadata.get("params", [])) or "none"
        prompt = (
            f"Write a concise, single-sentence docstring summary for a Python function named `{metadata['name']}`.\n"
            f"Parameters: {param_str}\n"
            f"Returns: {metadata.get('return_type', 'None')}\n\n"
            "Rules:\n"
            "- Return ONLY the summary sentence itself (max 15 words).\n"
            "- Do not include quotes, 'Args:', 'Returns:', or any section headers.\n"
            "- Start with a verb (e.g. Calculates, Fetches, Validates).\n"
            "- Be specific to the function name and parameters."
        )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.url,
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 60,
                        }
                    }
                )
                response.raise_for_status()
                summary = response.json().get("response", "").strip()

                # Strip surrounding quotes if LLM adds them
                if len(summary) >= 2 and summary[0] in ('"', "'") and summary[-1] == summary[0]:
                    summary = summary[1:-1].strip()

                # Strip verbose prefixes the LLM sometimes adds
                import re
                summary = re.sub(r'^here is a concise docstring summary[^:]*:\s*', '', summary, flags=re.IGNORECASE)
                summary = re.sub(r'^here is a[^:]*:\s*', '', summary, flags=re.IGNORECASE)
                summary = re.sub(r'^docstring:\s*', '', summary, flags=re.IGNORECASE)
                summary = re.sub(r'^summary:\s*', '', summary, flags=re.IGNORECASE)
                summary = summary.strip()

                # Take only first sentence
                for ch in (".", "\n"):
                    idx = summary.find(ch)
                    if idx != -1 and idx > 10:
                        summary = summary[:idx + 1]
                        break

                return summary if summary else None

        except Exception as e:
            print(f"OllamaProvider: Error calling Llama 3 — {e}")
            return None
