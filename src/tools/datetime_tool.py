from datetime import datetime, timedelta
from typing import Any
import re
from .base import BaseTool


class DateTimeTool(BaseTool):
    """"日期时间工具"""
    
    def __init__(self):
        super().__init__(
            name="datetime",
            description="获取当前日期、时间、星期几，或计算相对日期"
        )
    
    def execute(self, action: str = "now", **kwargs) -> Any:
        """"执行日期时间操作"""
        now = datetime.now()
        
        # 处理相对日期 (+N 或 -N)
        offset_match = re.match(r'^([+-])(\d+)$', action)
        if offset_match:
            sign = 1 if offset_match.group(1) == '+' else -1
            days = int(offset_match.group(2)) * sign
            target = now + timedelta(days=days)
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            return {
                "success": True,
                "date": target.strftime("%Y-%m-%d"),
                "weekday": weekdays[target.weekday()],
                "description": f"{action}天后的日期"
            }
        
        # 处理中文相对日期
        if action == "大后天" or action == "大后天":
            target = now + timedelta(days=3)
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            return {
                "success": True,
                "date": target.strftime("%Y-%m-%d"),
                "weekday": weekdays[target.weekday()],
                "description": "大后天"
            }
        elif action == "后天":
            target = now + timedelta(days=2)
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            return {
                "success": True,
                "date": target.strftime("%Y-%m-%d"),
                "weekday": weekdays[target.weekday()],
                "description": "后天"
            }
        elif action == "明天":
            target = now + timedelta(days=1)
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            return {
                "success": True,
                "date": target.strftime("%Y-%m-%d"),
                "weekday": weekdays[target.weekday()],
                "description": "明天"
            }
        elif action == "昨天":
            target = now - timedelta(days=1)
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            return {
                "success": True,
                "date": target.strftime("%Y-%m-%d"),
                "weekday": weekdays[target.weekday()],
                "description": "昨天"
            }
        elif action == "前天":
            target = now - timedelta(days=2)
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            return {
                "success": True,
                "date": target.strftime("%Y-%m-%d"),
                "weekday": weekdays[target.weekday()],
                "description": "前天"
            }
        elif action == "大前天":
            target = now - timedelta(days=3)
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            return {
                "success": True,
                "date": target.strftime("%Y-%m-%d"),
                "weekday": weekdays[target.weekday()],
                "description": "大前天"
            }
        elif action == "now":
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
                "weekday": weekdays[now.weekday()],
                "date": now.strftime("%Y-%m-%d")
            }
        elif action == "tomorrow":
            target = now + timedelta(days=1)
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            return {
                "success": True,
                "date": target.strftime("%Y-%m-%d"),
                "weekday": weekdays[target.weekday()]
            }
        elif action == "yesterday":
            target = now - timedelta(days=1)
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            return {
                "success": True,
                "date": target.strftime("%Y-%m-%d"),
                "weekday": weekdays[target.weekday()]
            }
        else:
            # 尝试解析日期字符串
            try:
                target_date = datetime.strptime(action, "%Y-%m-%d")
                weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
                return {
                    "success": True,
                    "date": target_date.strftime("%Y-%m-%d"),
                    "weekday": weekdays[target_date.weekday()]
                }
            except ValueError:
                return {"success": False, "error": f"未知操作: {action}"}
