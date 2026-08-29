from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseTool(ABC):
    """"工具基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """"执行工具"""
        raise NotImplementedError("子类必须实现execute方法")
    
    def __repr__(self):
        return f"<Tool: {self.name}>"


class ToolRegistry:
    """"工具注册表"""
    
    def __init__(self):
        self._tools = {}
    
    def register(self, tool: BaseTool) -> None:
        """"注册工具"""
        if not isinstance(tool, BaseTool):
            raise TypeError("工具必须是BaseTool的实例")
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """"按名称获取工具"""
        return self._tools.get(name)
    
    def list_tools(self) -> list:
        """"列出所有工具"""
        return list(self._tools.values())
    
    def has_tool(self, name: str) -> bool:
        """"检查工具是否存在"""
        return name in self._tools
