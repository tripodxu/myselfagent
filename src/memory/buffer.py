import json
from pathlib import Path
from typing import Any, List, Dict, Optional
from datetime import datetime
from .base import BaseMemory


class BufferMemory(BaseMemory):
    """"基础缓冲记忆实现"""
    
    def __init__(self, max_size: int = 100, persist_path: str = None):
        super().__init__()
        self.max_size = max_size
        self.persist_path = persist_path
        
        # 如果有持久化路径，尝试加载
        if persist_path and Path(persist_path).exists():
            self._load()
    
    def add_message(self, role: str, content: str, metadata: Dict = None) -> None:
        """"添加消息"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.messages.append(message)
        
        # 如果超过最大大小，移除最旧的消息
        if len(self.messages) > self.max_size:
            self.messages = self.messages[-self.max_size:]
        
        # 自动持久化
        if self.persist_path:
            self._save()
    
    def get_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """"获取历史消息"""
        if limit:
            return self.messages[-limit:]
        return self.messages.copy()
    
    def clear(self) -> None:
        """"清除记忆"""
        self.messages = []
        
        # 清除持久化文件
        if self.persist_path and Path(self.persist_path).exists():
            Path(self.persist_path).unlink()
    
    def get_context_window(self, window_size: int = 10) -> List[Dict[str, Any]]:
        """"获取上下文窗口"""
        return super().get_context_window(window_size)
    
    def _save(self) -> None:
        """"保存到文件"""
        try:
            data = {
                "messages": self.messages,
                "max_size": self.max_size,
                "saved_at": datetime.now().isoformat()
            }
            
            Path(self.persist_path).write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"保存记忆失败: {e}")
    
    def _load(self) -> None:
        """"从文件加载"""
        try:
            data = json.loads(
                Path(self.persist_path).read_text(encoding="utf-8")
            )
            self.messages = data.get("messages", [])
            self.max_size = data.get("max_size", self.max_size)
        except Exception as e:
            print(f"加载记忆失败: {e}")
