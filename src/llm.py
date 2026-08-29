import time
import requests
from typing import Optional, List
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun


class LocalLLM(LLM):
    """Local API LLM with reasoning effort control"""

    api_base: str = "http://127.0.0.1:8788"
    api_path: str = "/v1/responses"
    model_name: str = "mimo-v2.5-pro"
    timeout: int = 60
    max_retries: int = 3
    reasoning_effort: str = "medium"

    @property
    def _llm_type(self) -> str:
        return "local"

    def _call(self, prompt: str, stop: Optional[List[str]] = None,
              run_manager: Optional[CallbackManagerForLLMRun] = None) -> str:
        url = f"{self.api_base}{self.api_path}"
        payload = {"model": self.model_name, "input": prompt}
        if stop:
            payload["stop"] = stop
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()
                if "output" in result:
                    for item in result["output"]:
                        if item.get("type") == "message":
                            for c in item.get("content", []):
                                if c.get("type") == "output_text":
                                    return c.get("text", "")
                    return str(result["output"])
                elif "choices" in result:
                    return result["choices"][0]["message"]["content"]
                return str(result)
            except requests.Timeout as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise Exception(f"Timeout (retried {self.max_retries}x): {e}")
            except requests.RequestException as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise Exception(f"Request failed (retried {self.max_retries}x): {e}")
        raise Exception(f"All retries failed: {last_exception}")

    def set_reasoning_effort(self, effort: str):
        """Set reasoning effort: low, medium, high"""
        self.reasoning_effort = effort

    @property
    def _identifying_params(self) -> dict:
        return {"api_base": self.api_base, "api_path": self.api_path,
                "model_name": self.model_name, "reasoning_effort": self.reasoning_effort}
