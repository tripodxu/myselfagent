import subprocess
import sys
import os
from typing import Any
from .base import BaseTool


# 被禁止导入的模块（只禁止真正危险的）
BLOCKED_IMPORTS = [
    "subprocess", "shutil", "importlib",
    "ctypes", "socket", "http", "ftplib", "smtplib",
]


class PythonExecTool(BaseTool):
    """Python代码执行工具"""

    def __init__(self, timeout: int = 10):
        super().__init__(
            name="python_exec",
            description="执行Python代码并返回结果"
        )
        self.timeout = timeout

    def execute(self, code: str, **kwargs) -> Any:
        """执行Python代码"""
        # 检查是否有被禁止的导入
        self._check_blocked_imports(code)

        try:
            # 修复Windows编码：强制子进程使用UTF-8
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=kwargs.get("cwd", "."),
                encoding='utf-8',
                errors='replace',
                env=env
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "output": result.stdout,
                    "error": result.stderr
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": f"执行超时 (超过{self.timeout}秒)"
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }

    def _check_blocked_imports(self, code: str) -> None:
        """检查代码中是否有被禁止的导入"""
        import ast
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in BLOCKED_IMPORTS:
                            raise ImportError(f"禁止导入模块: {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split(".")[0] in BLOCKED_IMPORTS:
                        raise ImportError(f"禁止从 {node.module} 导入")
        except SyntaxError:
            pass  # 语法错误会在执行时被捕获
