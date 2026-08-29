import subprocess
import sys
import os
from typing import Any, Dict
from .base import BaseTool

BLOCKED_IMPORTS = ["subprocess", "shutil", "importlib", "ctypes", "socket", "http", "ftplib", "smtplib"]


class PythonExecTool(BaseTool):
    def __init__(self, timeout: int = 10):
        super().__init__(name="python_exec", description="Execute Python code and return output")
        self.timeout = timeout

    def parameters_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}

    def execute(self, code: str = "", **kwargs) -> Any:
        self._check_blocked_imports(code)
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            result = subprocess.run([sys.executable, "-c", code],
                capture_output=True, text=True, timeout=self.timeout,
                cwd=kwargs.get("cwd", "."), encoding="utf-8", errors="replace", env=env)
            if result.returncode == 0:
                return {"success": True, "output": result.stdout, "error": None}
            return {"success": False, "output": result.stdout, "error": result.stderr}
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": "\u6267\u884c\u8d85\u65f6 (" + str(self.timeout) + "\u79d2)"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    def _check_blocked_imports(self, code: str) -> None:
        import ast
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in BLOCKED_IMPORTS:
                            raise ImportError("\u7981\u6b62\u5bfc\u5165\u6a21\u5757: " + alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split(".")[0] in BLOCKED_IMPORTS:
                        raise ImportError("\u7981\u6b62\u4ece " + node.module + " \u5bfc\u5165")
        except SyntaxError: pass
