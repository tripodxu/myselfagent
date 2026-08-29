import pytest
from src.memory.base import BaseMemory


# 创建一个具体的记忆实现用于测试
class ConcreteMemory(BaseMemory):
    def add_message(self, role: str, content: str, metadata: dict = None):
        self.messages.append({
            "role": role,
            "content": content,
            "metadata": metadata or {}
        })
    
    def get_history(self, limit: int = None):
        if limit:
            return self.messages[-limit:]
        return self.messages.copy()
    
    def clear(self):
        self.messages = []


class TestBaseMemory:
    def test_memory_initialization(self):
        """"测试记忆系统初始化"""
        memory = ConcreteMemory()
        assert len(memory.messages) == 0
    
    def test_memory_add_message(self):
        """"测试添加消息"""
        memory = ConcreteMemory()
        memory.add_message("user", "Hello")
        
        assert len(memory.messages) == 1
        assert memory.messages[0]["role"] == "user"
        assert memory.messages[0]["content"] == "Hello"
    
    def test_memory_get_history(self):
        """"测试获取历史"""
        memory = ConcreteMemory()
        memory.add_message("user", "Hello")
        memory.add_message("assistant", "Hi there")
        
        history = memory.get_history()
        assert len(history) == 2
        assert history[0]["content"] == "Hello"
        assert history[1]["content"] == "Hi there"
    
    def test_memory_clear(self):
        """"测试清除记忆"""
        memory = ConcreteMemory()
        memory.add_message("user", "Hello")
        memory.add_message("assistant", "Hi")
        
        memory.clear()
        assert len(memory.messages) == 0
    
    def test_get_context_window(self):
        """"测试获取上下文窗口"""
        memory = ConcreteMemory()
        for i in range(20):
            memory.add_message("user", f"Message {i}")
        
        window = memory.get_context_window(5)
        assert len(window) == 5
        assert window[0]["content"] == "Message 15"
        assert window[-1]["content"] == "Message 19"
    
    def test_search_messages(self):
        """"测试搜索消息"""
        memory = ConcreteMemory()
        memory.add_message("user", "Hello World")
        memory.add_message("assistant", "Hi there")
        memory.add_message("user", "Hello again")
        
        results = memory.search_messages("Hello")
        assert len(results) == 2
    
    def test_get_summary(self):
        """"测试获取摘要"""
        memory = ConcreteMemory()
        memory.add_message("user", "Hello")
        memory.add_message("assistant", "Hi")
        
        summary = memory.get_summary()
        assert summary["total_messages"] == 2
        assert summary["first_message"]["content"] == "Hello"
        assert summary["last_message"]["content"] == "Hi"
