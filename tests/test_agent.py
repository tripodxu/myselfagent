import pytest
from unittest.mock import MagicMock, patch
from src.agent import Agent
from src.llm import LocalLLM
from src.tools.base import BaseTool, ToolRegistry
from src.memory.buffer import BufferMemory
from src.planner.simple import SimplePlanner


# 创建测试工具
class MockTool(BaseTool):
    def __init__(self):
        super().__init__("mock_tool", "Mock tool for testing")
    
    def execute(self, **kwargs):
        return {"success": True, "result": "mock result"}


class FailingTool(BaseTool):
    def __init__(self):
        super().__init__("failing_tool", "Tool that always fails")
    
    def execute(self, **kwargs):
        return {"success": False, "error": "Tool execution failed"}


class TestAgent:
    def setup_method(self):
        self.mock_llm = MagicMock(spec=LocalLLM)
        self.memory = BufferMemory()
        self.planner = SimplePlanner(max_steps=3)
        self.registry = ToolRegistry()
        self.registry.register(MockTool())
    
    def test_agent_initialization(self):
        """"测试Agent初始化"""
        agent = Agent(
            llm=self.mock_llm,
            memory=self.memory,
            planner=self.planner,
            tool_registry=self.registry
        )
        
        assert agent.llm is not None
        assert agent.memory is not None
        assert agent.planner is not None
        assert agent.tool_registry is not None
    
    def test_agent_run_single_step(self):
        """"测试单步执行"""
        # Mock LLM返回
        self.mock_llm._call.return_value = '{"tool": "mock_tool", "params": {}}'
        
        agent = Agent(
            llm=self.mock_llm,
            memory=self.memory,
            planner=self.planner,
            tool_registry=self.registry,
            max_iterations=1
        )
        
        result = agent.run("测试目标")
        
        assert result["goal"] == "测试目标"
        assert result["iterations"] >= 1
    
    def test_agent_run_full_cycle(self):
        """"测试完整循环"""
        # Mock LLM返回
        self.mock_llm._call.return_value = '{"tool": "mock_tool", "params": {}}'
        
        agent = Agent(
            llm=self.mock_llm,
            memory=self.memory,
            planner=self.planner,
            tool_registry=self.registry,
            max_iterations=5
        )
        
        result = agent.run("测试目标")
        
        assert result["goal"] == "测试目标"
        assert result["iterations"] > 0
        assert result["plan_status"] in ["completed", "active"]
    
    def test_agent_handles_tool_error(self):
        """"测试工具执行错误处理"""
        # 注册失败工具
        self.registry.register(FailingTool())
        
        # Mock LLM返回失败工具
        self.mock_llm._call.return_value = '{"tool": "failing_tool", "params": {}}'
        
        agent = Agent(
            llm=self.mock_llm,
            memory=self.memory,
            planner=self.planner,
            tool_registry=self.registry,
            max_iterations=1
        )
        
        result = agent.run("测试目标")
        
        # Agent应该能处理错误并继续
        assert result["goal"] == "测试目标"
    
    def test_agent_stores_memory(self):
        """"测试结果存入记忆"""
        self.mock_llm._call.return_value = '{"tool": "mock_tool", "params": {}}'
        
        agent = Agent(
            llm=self.mock_llm,
            memory=self.memory,
            planner=self.planner,
            tool_registry=self.registry,
            max_iterations=1
        )
        
        agent.run("测试目标")
        
        # 检查记忆中是否有记录
        history = self.memory.get_history()
        assert len(history) > 0
    
    def test_agent_no_memory(self):
        """"测试无记忆系统"""
        self.mock_llm._call.return_value = '{"tool": "mock_tool", "params": {}}'
        
        agent = Agent(
            llm=self.mock_llm,
            memory=None,
            planner=self.planner,
            tool_registry=self.registry,
            max_iterations=1
        )
        
        result = agent.run("测试目标")
        
        assert result["goal"] == "测试目标"
    
    def test_agent_max_iterations(self):
        """"测试最大迭代次数"""
        self.mock_llm._call.return_value = '{"tool": "mock_tool", "params": {}}'
        
        agent = Agent(
            llm=self.mock_llm,
            memory=self.memory,
            planner=self.planner,
            tool_registry=self.registry,
            max_iterations=2
        )
        
        result = agent.run("测试目标")
        
        assert result["iterations"] <= 2
    
    def test_agent_invalid_json_response(self):
        """"测试LLM返回无效JSON"""
        self.mock_llm._call.return_value = "这不是JSON"
        
        agent = Agent(
            llm=self.mock_llm,
            memory=self.memory,
            planner=self.planner,
            tool_registry=self.registry,
            max_iterations=1
        )
        
        result = agent.run("测试目标")
        
        # Agent应该能处理无效响应
        assert result["goal"] == "测试目标"
    
    def test_get_memory_summary(self):
        """"测试获取记忆摘要"""
        self.mock_llm._call.return_value = '{"tool": "mock_tool", "params": {}}'
        
        agent = Agent(
            llm=self.mock_llm,
            memory=self.memory,
            planner=self.planner,
            tool_registry=self.registry,
            max_iterations=1
        )
        
        agent.run("测试目标")
        
        summary = agent.get_memory_summary()
        assert "total_messages" in summary
        assert summary["total_messages"] > 0
    
    def test_get_memory_summary_no_memory(self):
        """"测试无记忆时获取摘要"""
        agent = Agent(
            llm=self.mock_llm,
            memory=None,
            planner=self.planner,
            tool_registry=self.registry
        )
        
        summary = agent.get_memory_summary()
        assert "error" in summary
