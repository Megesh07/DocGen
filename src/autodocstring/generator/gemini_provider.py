import os
import json
import httpx
from typing import Dict, Any, Optional

class GeminiProvider:
    """LLM Provider for Google Gemini API."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

    def generate_summary(self, metadata: Dict[str, Any]) -> Optional[str]:
        """Generate a concise summary sentence using Gemini for the given function metadata.
        
        Args:
            metadata: Dictionary containing 'name', 'params', 'return_type', and 'raises'.
            
        Returns:
            A string containing the summary sentence, or None if failed.
        """
        if not self.api_key:
            print("GeminiProvider Error: No API key found in environment variable GEMINI_API_KEY")
            return None

        prompt = (
            f"Write a concise, single-sentence docstring summary for a Python function named `{metadata['name']}`.\n"
            f"Parameters: {', '.join(metadata['params']) if metadata['params'] else 'None'}\n"
            f"Returns: {metadata['return_type']}\n\n"
            "Return ONLY the summary sentence itself. Do not include quotes, 'Args:', or any additional text."
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topK": 1,
                "topP": 1,
                "maxOutputTokens": 100,
            }
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.url}?key={self.api_key}",
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()
                
                # Extract text from candidate
                candidates = result.get("candidates", [])
                if not candidates:
                    return None
                    
                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                
                # Strip quotes if the LLM adds them
                if text.startswith('"') and text.endswith('"'):
                    text = text[1:-1]
                if text.startswith("'") and text.endswith("'"):
                    text = text[1:-1]

                # Strip verbose prefixes the LLM sometimes adds
                import re
                text = re.sub(r'^here is a concise docstring summary[^:]*:\s*', '', text, flags=re.IGNORECASE)
                text = re.sub(r'^here is a[^:]*:\s*', '', text, flags=re.IGNORECASE)
                text = re.sub(r'^docstring:\s*', '', text, flags=re.IGNORECASE)
                text = re.sub(r'^summary:\s*', '', text, flags=re.IGNORECASE)
                # Take only the first sentence if multi-sentence
                for ch in (".", "\n"):
                    idx = text.find(ch)
                    if idx != -1 and idx > 10:
                        text = text[:idx + 1]
                        break
                text = text.strip()
                    
                return text if text else None
        except Exception as e:
            print(f"GeminiProvider API Error: {e}")
            return None
