from datetime import datetime
from typing import Any
from .base import BaseTool


class DateTimeTool(BaseTool):
    """"日期时间工具"""
    
    def __init__(self):
        super().__init__(
            name="datetime",
            description="获取当前日期、时间、星期几"
        )
    
    def execute(self, action: str = "now", **kwargs) -> Any:
        """"执行日期时间操作"""
        now = datetime.now()
        
        if action == "now":
            return {
                "success": True,
                "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S")
            }
        elif action == "date":
            return {
                "success": True,
                "date": now.strftime("%Y-%m-%d")
            }
        elif action == "time":
            return {
                "success": True,
                "time": now.strftime("%H:%M:%S")
            }
        elif action == "weekday":
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            return {
                "success": True,
                "weekday": weekdays[now.weekday()]
            }
        else:
            return {"success": False, "error": f"未知操作: {action}"}
