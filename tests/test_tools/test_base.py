import pytest
from src.tools.base import BaseTool, ToolRegistry


# 创建一个具体的工具实现用于测试
class ConcreteTool(BaseTool):
    def execute(self, **kwargs):
        return "executed"


class TestBaseTool:
    def test_tool_initialization(self):
        """"测试工具能正确初始化"""
        tool = ConcreteTool("test", "A test tool")
        assert tool.name == "test"
        assert tool.description == "A test tool"
    
    def test_tool_has_name(self):
        """"测试工具必须有名称"""
        tool = ConcreteTool("my_tool", "Description")
        assert tool.name == "my_tool"
    
    def test_tool_has_description(self):
        """"测试工具必须有描述"""
        tool = ConcreteTool("tool", "My description")
        assert tool.description == "My description"
    
    def test_tool_execute_not_implemented(self):
        """"测试基类execute方法抛出异常"""
        # BaseTool是抽象类，不能直接实例化
        with pytest.raises(TypeError):
            BaseTool("test", "test")
    
    def test_tool_repr(self):
        """"测试工具的字符串表示"""
        tool = ConcreteTool("search", "Search tool")
        assert repr(tool) == "<Tool: search>"


class TestToolRegistry:
    def test_register_tool(self):
        """"测试注册工具"""
        registry = ToolRegistry()
        tool = ConcreteTool("test", "Test tool")
        registry.register(tool)
        assert registry.has_tool("test")
    
    def test_get_tool_by_name(self):
        """"测试按名称获取工具"""
        registry = ToolRegistry()
        tool = ConcreteTool("search", "Search tool")
        registry.register(tool)
        retrieved = registry.get_tool("search")
        assert retrieved is tool
    
    def test_list_all_tools(self):
        """"测试列出所有工具"""
        registry = ToolRegistry()
        tool1 = ConcreteTool("tool1", "First tool")
        tool2 = ConcreteTool("tool2", "Second tool")
        registry.register(tool1)
        registry.register(tool2)
        
        tools = registry.list_tools()
        assert len(tools) == 2
        assert tool1 in tools
        assert tool2 in tools
    
    def test_get_nonexistent_tool(self):
        """"测试获取不存在的工具"""
        registry = ToolRegistry()
        result = registry.get_tool("nonexistent")
        assert result is None
    
    def test_register_non_tool_raises_error(self):
        """"测试注册非工具对象抛出错误"""
        registry = ToolRegistry()
        with pytest.raises(TypeError):
            registry.register("not a tool")
