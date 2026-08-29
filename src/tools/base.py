from abc import ABC, abstractmethod
from typing import Any, Optional, Dict


class BaseTool(ABC):
    """Tool base class with JSON Schema support"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        raise NotImplementedError

    def parameters_schema(self) -> Dict[str, Any]:
        """Return JSON Schema for parameters. Override in subclasses."""
        return {"type": "object", "properties": {}, "required": []}

    def to_tool_definition(self) -> Dict[str, Any]:
        """Generate structured tool definition for LLM."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema()
        }

    def __repr__(self):
        return f"<Tool: {self.name}>"


class ToolRegistry:
    """Tool registry with schema export"""

    def __init__(self):
        self._tools = {}

    def register(self, tool: BaseTool) -> None:
        if not isinstance(tool, BaseTool):
            raise TypeError("tool must be a BaseTool instance")
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> list:
        return list(self._tools.values())

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def get_tool_definitions(self) -> list:
        """Return structured tool definitions for LLM."""
        return [t.to_tool_definition() for t in self._tools.values()]
