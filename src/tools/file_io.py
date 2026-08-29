import os
from pathlib import Path
from typing import Any, List, Dict
from .base import BaseTool


class FileIOTool(BaseTool):
    def __init__(self, allowed_paths: List[str] = None):
        super().__init__(name="file_io", description="File operations: read, write, list directory")
        self.allowed_paths = allowed_paths or ["."]

    def parameters_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {
            "action": {"type": "string", "enum": ["read", "write", "list"]},
            "path": {"type": "string"},
            "content": {"type": "string"}
        }, "required": ["action", "path"]}

    def execute(self, action: str = "", path: str = "", content: str = None, **kwargs) -> Any:
        if action == "read": return self.read_file(path)
        elif action == "write":
            if content is None: return {"success": False, "error": "\u5199\u5165\u64cd\u4f5c\u9700\u8981content\u53c2\u6570"}
            return self.write_file(path, content)
        elif action == "list": return self.list_directory(path)
        return {"success": False, "error": "\u672a\u77e5\u64cd\u4f5c: " + action}

    def read_file(self, path: str) -> dict:
        try:
            self._check_path_allowed(path)
            p = Path(path)
            if not p.exists(): return {"success": False, "error": "\u6587\u4ef6\u4e0d\u5b58\u5728: " + path}
            if not p.is_file(): return {"success": False, "error": "\u4e0d\u662f\u6587\u4ef6: " + path}
            return {"success": True, "content": p.read_text(encoding="utf-8")}
        except PermissionError: return {"success": False, "error": "\u6ca1\u6709\u6743\u9650\u8bbf\u95ee: " + path}
        except Exception as e: return {"success": False, "error": str(e)}

    def write_file(self, path: str, content: str) -> dict:
        try:
            self._check_path_allowed(path)
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"success": True, "message": "\u6587\u4ef6\u5df2\u5199\u5165: " + path}
        except PermissionError: return {"success": False, "error": "\u6ca1\u6709\u6743\u9650\u5199\u5165: " + path}
        except Exception as e: return {"success": False, "error": str(e)}

    def list_directory(self, path: str) -> dict:
        try:
            self._check_path_allowed(path)
            d = Path(path)
            if not d.exists(): return {"success": False, "error": "\u76ee\u5f55\u4e0d\u5b58\u5728: " + path}
            if not d.is_dir(): return {"success": False, "error": "\u4e0d\u662f\u76ee\u5f55: " + path}
            items = [{"name": i.name, "type": "dir" if i.is_dir() else "file"} for i in d.iterdir()]
            return {"success": True, "items": items}
        except Exception as e: return {"success": False, "error": str(e)}

    def _check_path_allowed(self, path: str) -> None:
        abs_path = os.path.abspath(path)
        for allowed in self.allowed_paths:
            if abs_path.startswith(os.path.abspath(allowed)): return
        raise PermissionError("\u8def\u5f84\u4e0d\u5728\u5141\u8bb8\u8303\u56f4\u5185: " + path)
