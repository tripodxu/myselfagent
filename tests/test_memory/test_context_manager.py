import pytest
import json
from unittest.mock import MagicMock
from src.memory.context_manager import ContextManager
from src.memory.buffer import BufferMemory


class TestContextManager:
    def setup_method(self):
        self.memory = BufferMemory()
        self.cm = ContextManager(memory=self.memory, max_tokens=200)

    def test_init(self):
        assert self.cm.max_tokens == 200
        assert self.cm.memory is self.memory

    def test_add_message_stores_in_memory(self):
        self.cm.add_message("user", "hello")
        history = self.memory.get_history()
        assert len(history) == 1
        assert history[0]["role"] == "user"

    def test_add_message_tracks_tokens(self):
        self.cm.add_message("user", "hello world")
        stats = self.cm.get_stats()
        assert stats["total_messages"] == 1
        assert stats["estimated_tokens"] > 0

    def test_get_context_returns_recent_messages(self):
        self.cm.add_message("user", "msg1")
        self.cm.add_message("assistant", "msg2")
        self.cm.add_message("user", "msg3")
        ctx = self.cm.get_context()
        assert len(ctx) == 3
        assert ctx[0]["content"] == "msg1"

    def test_tool_output_truncated_on_add(self):
        big_output = "x" * 2000
        self.cm.add_message("tool", big_output)
        # Check that the message was truncated in context_window
        tool_msgs = [m for m in self.cm.context_window if m["role"] == "tool"]
        assert len(tool_msgs) == 1
        assert len(tool_msgs[0]["content"]) <= 600
        assert "[truncated]" in tool_msgs[0]["content"]

    def test_get_context_within_token_budget(self):
        cm = ContextManager(memory=BufferMemory(), max_tokens=500)
        for i in range(20):
            cm.add_message("user", f"message number {i} with some content here")
        ctx = cm.get_context(max_tokens=100)
        total_chars = sum(len(m["content"]) for m in ctx)
        assert total_chars <= 100 * 2 + 100

    def test_auto_compression_when_over_limit(self):
        cm = ContextManager(memory=self.memory, max_tokens=50)
        for i in range(10):
            cm.add_message("user", f"this is a fairly long message number {i}")
        stats = cm.get_stats()
        assert stats["estimated_tokens"] <= cm.max_tokens * 2

    def test_get_stats(self):
        self.cm.add_message("user", "hello")
        self.cm.add_message("assistant", "world")
        stats = self.cm.get_stats()
        assert stats["total_messages"] == 2
        assert "estimated_tokens" in stats
        assert "max_tokens" in stats
        assert "utilization" in stats

    def test_summarize_messages(self):
        messages = [
            {"role": "user", "content": "create a file" * 10},
            {"role": "assistant", "content": "file created" * 10},
        ]
        summary = self.cm._summarize_messages(messages)
        assert "create a file" in summary
        assert len(summary) < sum(len(m["content"]) for m in messages)

    def test_context_preserves_system_messages(self):
        self.cm.add_message("system", "You are an agent")
        for i in range(10):
            self.cm.add_message("user", f"msg {i} " * 10)
        ctx = self.cm.get_context()
        system_msgs = [m for m in ctx if m["role"] == "system"]
        assert len(system_msgs) >= 1

    def test_clear_context(self):
        self.cm.add_message("user", "hello")
        self.cm.clear()
        stats = self.cm.get_stats()
        assert stats["total_messages"] == 0
