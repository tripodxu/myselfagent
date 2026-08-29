import os
from pathlib import Path
from typing import Any, List
from .base import BaseTool


class FileIOTool(BaseTool):
    """"文件读写工具"""
    
    def __init__(self, allowed_paths: List[str] = None):
        super().__init__(
            name="file_io",
            description="文件读写操作：读取、写入、列出目录"
        )
        self.allowed_paths = allowed_paths or ["."]
    
    def execute(self, action: str, path: str, content: str = None, **kwargs) -> Any:
        """"执行文件操作"""
        if action == "read":
            return self.read_file(path)
        elif action == "write":
            if content is None:
                return {"success": False, "error": "写入操作需要content参数"}
            return self.write_file(path, content)
        elif action == "list":
            return self.list_directory(path)
        else:
            return {"success": False, "error": f"未知操作: {action}"}
    
    def read_file(self, path: str) -> dict:
        """"读取文件"""
        try:
            self._check_path_allowed(path)
            file_path = Path(path)
            
            if not file_path.exists():
                return {"success": False, "error": f"文件不存在: {path}"}
            
            if not file_path.is_file():
                return {"success": False, "error": f"不是文件: {path}"}
            
            content = file_path.read_text(encoding="utf-8")
            return {"success": True, "content": content}
            
        except PermissionError:
            return {"success": False, "error": f"没有权限读取: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def write_file(self, path: str, content: str) -> dict:
        """"写入文件"""
        try:
            self._check_path_allowed(path)
            file_path = Path(path)
            
            # 创建父目录（如果不存在）
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_path.write_text(content, encoding="utf-8")
            return {"success": True, "message": f"文件已写入: {path}"}
            
        except PermissionError:
            return {"success": False, "error": f"没有权限写入: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_directory(self, path: str) -> dict:
        """"列出目录内容"""
        try:
            self._check_path_allowed(path)
            dir_path = Path(path)
            
            if not dir_path.exists():
                return {"success": False, "error": f"目录不存在: {path}"}
            
            if not dir_path.is_dir():
                return {"success": False, "error": f"不是目录: {path}"}
            
            items = []
            for item in dir_path.iterdir():
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None
                })
            
            return {"success": True, "items": items}
            
        except PermissionError:
            return {"success": False, "error": f"没有权限访问: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _check_path_allowed(self, path: str) -> None:
        """"检查路径是否在允许范围内"""
        abs_path = os.path.abspath(path)
        
        for allowed in self.allowed_paths:
            allowed_abs = os.path.abspath(allowed)
            if abs_path.startswith(allowed_abs):
                return
        
        raise PermissionError(f"路径不在允许范围内: {path}")
