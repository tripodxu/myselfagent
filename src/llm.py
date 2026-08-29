import sys
import time
import json
import requests
from typing import Optional, List
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun


class LocalLLM(LLM):
    """Local API LLM with streaming support"""

    api_base: str = "http://127.0.0.1:8788"
    api_path: str = "/v1/responses"
    model_name: str = "oxx"
    timeout: int = 120
    max_retries: int = 3
    reasoning_effort: str = "medium"
    use_stream: bool = True
    debug: bool = False

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
                if self.use_stream:
                    return self._call_streaming(url, payload)
                else:
                    return self._call_sync(url, payload)
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

    def _call_streaming(self, url: str, payload: dict) -> str:
        """Streaming call: parse SSE, print chunks in real-time, return full text."""
        payload["stream"] = True
        response = requests.post(url, json=payload, timeout=self.timeout, stream=True)
        response.raise_for_status()

        collected = []
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                event = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            # OpenAI responses API streaming events
            etype = event.get("type", "")

            # response.output_text.delta -> {"type":"response.output_text.delta","delta":"text"}
            if etype == "response.output_text.delta":
                chunk = event.get("delta", "")
                if chunk:
                    collected.append(chunk)
                    if self.debug:
                        try:
                            sys.stdout.write(chunk)
                            sys.stdout.flush()
                        except (UnicodeEncodeError, ValueError):
                            pass

            # OpenAI chat completions streaming (fallback)
            elif etype == "" and "choices" in event:
                delta = event.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    collected.append(content)
                    if self.debug:
                        try:
                            sys.stdout.write(content)
                            sys.stdout.flush()
                        except (UnicodeEncodeError, ValueError):
                            pass

        if self.debug and collected:
            try:
                sys.stdout.write("\n")
                sys.stdout.flush()
            except (UnicodeEncodeError, ValueError):
                pass

        full_text = "".join(collected)
        if not full_text:
            # Fallback: maybe non-streaming response
            return self._call_sync(url, {k: v for k, v in payload.items() if k != "stream"})
        return full_text

    def _call_sync(self, url: str, payload: dict) -> str:
        """Non-streaming call: parse JSON response."""
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

    def set_reasoning_effort(self, effort: str):
        self.reasoning_effort = effort

    @property
    def _identifying_params(self) -> dict:
        return {"api_base": self.api_base, "api_path": self.api_path,
                "model_name": self.model_name, "reasoning_effort": self.reasoning_effort,
                "use_stream": self.use_stream}
