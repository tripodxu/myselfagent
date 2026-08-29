from datetime import datetime, timedelta
from typing import Any, Dict
import re
from .base import BaseTool


class DateTimeTool(BaseTool):
    """Date/time tool with Chinese date support"""

    WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def __init__(self):
        super().__init__(
            name="datetime",
            description="Get current date/time or compute relative dates"
        )

    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action: now, date, time, weekday, tomorrow, yesterday, +N, -N",
                    "default": "now"
                }
            },
            "required": []
        }

    def execute(self, action: str = "now", **kwargs) -> Any:
        now = datetime.now()
        offset = re.match(r"^([+-])(\d+)$", action)
        if offset:
            days = int(offset.group(2)) * (1 if offset.group(1) == "+" else -1)
            target = now + timedelta(days=days)
            return {"success": True, "date": target.strftime("%Y-%m-%d"), "weekday": self.WEEKDAYS[target.weekday()]}
        if action == "now":
            return {"success": True, "datetime": now.strftime("%Y-%m-%d %H:%M:%S"), "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M:%S")}
        if action == "date":
            return {"success": True, "date": now.strftime("%Y-%m-%d")}
        if action == "time":
            return {"success": True, "time": now.strftime("%H:%M:%S")}
        if action == "weekday":
            return {"success": True, "weekday": self.WEEKDAYS[now.weekday()], "date": now.strftime("%Y-%m-%d")}
        relative = {"tomorrow": 1, "yesterday": -1}
        if action in relative:
            target = now + timedelta(days=relative[action])
            return {"success": True, "date": target.strftime("%Y-%m-%d"), "weekday": self.WEEKDAYS[target.weekday()]}
        return {"success": False, "error": f"Unknown action: {action}"}
