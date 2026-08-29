import re
from pathlib import Path
from typing import Any, List, Dict
from .base import BaseTool


class SearchTool(BaseTool):
    def __init__(self):
        super().__init__(name="search", description="Search content in text or files")

    def parameters_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {
            "action": {"type": "string", "enum": ["text", "file", "files"]},
            "pattern": {"type": "string"},
            "text": {"type": "string"},
            "target": {"type": "string"}
        }, "required": ["action", "pattern"]}

    def execute(self, action: str = "", pattern: str = "", target: str = None, text: str = None, **kwargs) -> Any:
        if action == "text":
            if text is None: return {"success": False, "error": "\u6587\u672c\u641c\u7d22\u9700\u8981text\u53c2\u6570"}
            return self._search_text(pattern, text)
        elif action == "file":
            if not target: return {"success": False, "error": "\u6587\u4ef6\u641c\u7d22\u9700\u8981target\u53c2\u6570"}
            return self._search_file(pattern, target)
        elif action == "files":
            if not target: return {"success": False, "error": "\u591a\u6587\u4ef6\u641c\u7d22\u9700\u8981target\u53c2\u6570"}
            return self._search_files(pattern, target, **kwargs)
        return {"success": False, "error": "\u672a\u77e5\u641c\u7d22\u64cd\u4f5c: " + action}

    def _search_text(self, pattern: str, text: str) -> dict:
        try:
            matches = [{"line_number": i, "content": l.strip()} for i, l in enumerate(text.split("\n"), 1) if re.search(pattern, l, re.IGNORECASE)]
            return {"success": True, "matches": matches, "total": len(matches)}
        except re.error as e:
            return {"success": False, "error": "\u6b63\u5219\u8868\u8fbe\u5f0f\u9519\u8bef: " + str(e)}

    def _search_file(self, pattern: str, filepath: str) -> dict:
        try:
            p = Path(filepath)
            if not p.exists(): return {"success": False, "error": "\u6587\u4ef6\u4e0d\u5b58\u5728: " + filepath}
            return self._search_text(pattern, p.read_text(encoding="utf-8"))
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _search_files(self, pattern: str, directory: str, **kwargs) -> dict:
        try:
            d = Path(directory)
            if not d.exists(): return {"success": False, "error": "\u76ee\u5f55\u4e0d\u5b58\u5728: " + directory}
            extensions = kwargs.get("extensions")
            all_matches = []
            for f in d.rglob("*"):
                if not f.is_file(): continue
                if extensions and f.suffix not in extensions: continue
                try:
                    r = self._search_file(pattern, str(f))
                    if r.get("success") and r.get("total", 0) > 0:
                        all_matches.append({"file": str(f), "matches": r["matches"]})
                except Exception: continue
            return {"success": True, "files": all_matches, "total_files": len(all_matches)}
        except Exception as e:
            return {"success": False, "error": str(e)}
