import pytest
import os
import tempfile
import json
from src.memory.buffer import BufferMemory


class TestBufferMemory:
    def test_buffer_memory_store(self):
        """"测试存储消息"""
        memory = BufferMemory()
        memory.add_message("user", "Hello")
        memory.add_message("assistant", "Hi there")
        
        assert len(memory.messages) == 2
        assert memory.messages[0]["role"] == "user"
        assert memory.messages[1]["role"] == "assistant"
    
    def test_buffer_memory_retrieve(self):
        """"测试检索消息"""
        memory = BufferMemory()
        memory.add_message("user", "Hello")
        memory.add_message("assistant", "Hi")
        
        history = memory.get_history()
        assert len(history) == 2
        assert history[0]["content"] == "Hello"
        assert history[1]["content"] == "Hi"
    
    def test_buffer_memory_context_window(self):
        """"测试上下文窗口限制"""
        memory = BufferMemory()
        for i in range(20):
            memory.add_message("user", f"Message {i}")
        
        window = memory.get_context_window(5)
        assert len(window) == 5
        assert window[0]["content"] == "Message 15"
    
    def test_buffer_memory_max_size(self):
        """"测试最大容量限制"""
        memory = BufferMemory(max_size=5)
        
        for i in range(10):
            memory.add_message("user", f"Message {i}")
        
        assert len(memory.messages) == 5
        assert memory.messages[0]["content"] == "Message 5"
        assert memory.messages[-1]["content"] == "Message 9"
    
    def test_buffer_memory_persistence(self):
        """"测试记忆持久化（保存到文件）"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name
        
        try:
            # 创建并保存
            memory = BufferMemory(persist_path=temp_file)
            memory.add_message("user", "Hello")
            memory.add_message("assistant", "Hi")
            
            # 验证文件存在
            assert os.path.exists(temp_file)
            
            # 加载并验证
            loaded_memory = BufferMemory(persist_path=temp_file)
            assert len(loaded_memory.messages) == 2
            assert loaded_memory.messages[0]["content"] == "Hello"
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_buffer_memory_clear(self):
        """"测试清除记忆"""
        memory = BufferMemory()
        memory.add_message("user", "Hello")
        memory.add_message("assistant", "Hi")
        
        memory.clear()
        assert len(memory.messages) == 0
    
    def test_buffer_memory_clear_with_persistence(self):
        """"测试清除持久化记忆"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name
        
        try:
            memory = BufferMemory(persist_path=temp_file)
            memory.add_message("user", "Hello")
            
            assert os.path.exists(temp_file)
            
            memory.clear()
            assert len(memory.messages) == 0
            assert not os.path.exists(temp_file)
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_buffer_memory_metadata(self):
        """"测试消息元数据"""
        memory = BufferMemory()
        memory.add_message("user", "Hello", {"source": "test"})
        
        assert memory.messages[0]["metadata"]["source"] == "test"
    
    def test_buffer_memory_timestamp(self):
        """"测试消息时间戳"""
        memory = BufferMemory()
        memory.add_message("user", "Hello")
        
        assert "timestamp" in memory.messages[0]
        assert memory.messages[0]["timestamp"] is not None
