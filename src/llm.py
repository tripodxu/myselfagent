import time
import requests
from typing import Optional, List
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun


class LocalLLM(LLM):
    """"连接本地API的自定义LLM类"""
    
    api_base: str = "http://127.0.0.1:8788"
    api_path: str = "/v1/responses"
    model_name: str = "default"
    timeout: int = 30
    max_retries: int = 3
    
    @property
    def _llm_type(self) -> str:
        return "local"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
    ) -> str:
        """"调用本地API"""
        url = f"{self.api_base}{self.api_path}"
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }
        
        if stop:
            payload["stop"] = stop
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                result = response.json()
                
                # 兼容OpenAI格式响应
                if "choices" in result:
                    return result["choices"][0]["message"]["content"]
                elif "output" in result:
                    return result["output"]
                else:
                    return str(result)
                    
            except requests.Timeout as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                    continue
                raise Exception(f"请求超时 (已重试{self.max_retries}次): {e}")
            except requests.RequestException as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                    continue
                raise Exception(f"请求失败 (已重试{self.max_retries}次): {e}")
        
        raise Exception(f"所有重试都失败: {last_exception}")
    
    @property
    def _identifying_params(self) -> dict:
        return {
            "api_base": self.api_base,
            "api_path": self.api_path,
            "model_name": self.model_name,
        }
