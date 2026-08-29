import json
from typing import Any, List, Dict, Optional
from .base import BaseMemory


class ContextManager:
    CHARS_PER_TOKEN = 2
    TOOL_OUTPUT_MAX_CHARS = 500

    def __init__(self, memory=None, max_tokens=4000):
        self.memory = memory
        self.max_tokens = max_tokens
        self.context_window = []
        self.summary = ""

    def add_message(self, role, content, metadata=None):
        if role == "tool" and len(content) > self.TOOL_OUTPUT_MAX_CHARS:
            content = content[:self.TOOL_OUTPUT_MAX_CHARS] + "... [truncated]"
        message = {"role": role, "content": content}
        if metadata:
            message["metadata"] = metadata
        if self.memory:
            self.memory.add_message(role, content, metadata)
        self.context_window.append(message)
        self._auto_compress()

    def get_context(self, max_tokens=None):
        budget = max_tokens or self.max_tokens
        budget_chars = budget * self.CHARS_PER_TOKEN
        result = []
        system_msgs = [m for m in self.context_window if m["role"] == "system"]
        result.extend(system_msgs)
        used_chars = sum(len(m["content"]) for m in result)
        if self.summary:
            sm = {"role": "system", "content": "Previous context summary: " + self.summary}
            result.append(sm)
            used_chars += len(sm["content"])
        non_system = [m for m in self.context_window if m["role"] != "system"]
        recent = []
        for msg in reversed(non_system):
            mc = len(msg["content"])
            if used_chars + mc > budget_chars:
                break
            recent.insert(0, msg)
            used_chars += mc
        result.extend(recent)
        return result

    def get_stats(self):
        tc = sum(len(m["content"]) for m in self.context_window)
        et = tc // self.CHARS_PER_TOKEN
        return {
            "total_messages": len(self.context_window),
            "total_chars": tc,
            "estimated_tokens": et,
            "max_tokens": self.max_tokens,
            "utilization": round(et / self.max_tokens, 2) if self.max_tokens > 0 else 0,
            "has_summary": bool(self.summary),
            "summary_length": len(self.summary),
        }

    def clear(self):
        self.context_window = []
        self.summary = ""

    def _auto_compress(self):
        tc = sum(len(m["content"]) for m in self.context_window)
        if tc // self.CHARS_PER_TOKEN <= self.max_tokens:
            return
        sys_m = [m for m in self.context_window if m["role"] == "system"]
        ns = [m for m in self.context_window if m["role"] != "system"]
        if len(ns) <= 2:
            return
        sp = len(ns) // 2
        comp = self._summarize_messages(ns[:sp])
        if self.summary:
            self.summary = self.summary + "; " + comp
        else:
            self.summary = comp
        self.context_window = sys_m + ns[sp:]

    def _summarize_messages(self, messages):
        parts = []
        for msg in messages:
            c = msg["content"][:100]
            if len(msg["content"]) > 100:
                c += "..."
            parts.append(msg["role"] + ": " + c)
        return " | ".join(parts)
