from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional
from datetime import datetime


class BaseMemory(ABC):
    """"记忆系统基类"""
    
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
    
    @abstractmethod
    def add_message(self, role: str, content: str, metadata: Dict = None) -> None:
        """"添加消息"""
        raise NotImplementedError
    
    @abstractmethod
    def get_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """"获取历史消息"""
        raise NotImplementedError
    
    @abstractmethod
    def clear(self) -> None:
        """"清除记忆"""
        raise NotImplementedError
    
    def get_context_window(self, window_size: int = 10) -> List[Dict[str, Any]]:
        """"获取上下文窗口（最近N条消息）"""
        return self.messages[-window_size:] if self.messages else []
    
    def search_messages(self, keyword: str) -> List[Dict[str, Any]]:
        """"搜索包含关键词的消息"""
        return [msg for msg in self.messages if keyword.lower() in msg.get("content", "").lower()]
    
    def get_summary(self) -> Dict[str, Any]:
        """"获取记忆摘要"""
        return {
            "total_messages": len(self.messages),
            "first_message": self.messages[0] if self.messages else None,
            "last_message": self.messages[-1] if self.messages else None,
        }
