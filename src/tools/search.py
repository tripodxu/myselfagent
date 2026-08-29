import re
from pathlib import Path
from typing import Any, List, Dict
from .base import BaseTool


class SearchTool(BaseTool):
    """"搜索工具"""
    
    def __init__(self):
        super().__init__(
            name="search",
            description="在文本或文件中搜索内容"
        )
    
    def execute(self, action: str, pattern: str, target: str = None, text: str = None, **kwargs) -> Any:
        """"执行搜索"""
        if action == "text":
            if text is None:
                return {"success": False, "error": "文本搜索需要text参数"}
            return self.search_in_text(pattern, text)
        elif action == "file":
            if target is None:
                return {"success": False, "error": "文件搜索需要target参数"}
            return self.search_in_file(pattern, target)
        elif action == "files":
            if target is None:
                return {"success": False, "error": "多文件搜索需要target参数"}
            return self.search_in_files(pattern, target, **kwargs)
        else:
            return {"success": False, "error": f"未知搜索操作: {action}"}
    
    def search_in_text(self, pattern: str, text: str) -> dict:
        """"在文本中搜索"""
        try:
            matches = []
            for i, line in enumerate(text.split("\n"), 1):
                if re.search(pattern, line, re.IGNORECASE):
                    matches.append({
                        "line_number": i,
                        "content": line.strip()
                    })
            
            return {
                "success": True,
                "matches": matches,
                "total": len(matches)
            }
        except re.error as e:
            return {"success": False, "error": f"正则表达式错误: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_in_file(self, pattern: str, filepath: str) -> dict:
        """"在文件中搜索"""
        try:
            file_path = Path(filepath)
            
            if not file_path.exists():
                return {"success": False, "error": f"文件不存在: {filepath}"}
            
            if not file_path.is_file():
                return {"success": False, "error": f"不是文件: {filepath}"}
            
            content = file_path.read_text(encoding="utf-8")
            return self.search_in_text(pattern, content)
            
        except PermissionError:
            return {"success": False, "error": f"没有权限读取: {filepath}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_in_files(self, pattern: str, directory: str, extensions: List[str] = None, **kwargs) -> dict:
        """"在多个文件中搜索"""
        try:
            dir_path = Path(directory)
            
            if not dir_path.exists():
                return {"success": False, "error": f"目录不存在: {directory}"}
            
            if not dir_path.is_dir():
                return {"success": False, "error": f"不是目录: {directory}"}
            
            all_matches = []
            
            for file_path in dir_path.rglob("*"):
                if not file_path.is_file():
                    continue
                
                if extensions:
                    if file_path.suffix not in extensions:
                        continue
                
                try:
                    result = self.search_in_file(pattern, str(file_path))
                    if result["success"] and result["total"] > 0:
                        all_matches.append({
                            "file": str(file_path),
                            "matches": result["matches"]
                        })
                except Exception:
                    continue
            
            return {
                "success": True,
                "files": all_matches,
                "total_files": len(all_matches)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
