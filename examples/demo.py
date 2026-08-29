#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySelfAgent 演示脚本
演示Agent的基本功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm import LocalLLM
from src.tools.base import ToolRegistry
from src.tools.python_exec import PythonExecTool
from src.tools.file_io import FileIOTool
from src.tools.search import SearchTool
from src.memory.buffer import BufferMemory
from src.planner.simple import SimplePlanner
from src.agent import Agent


def main():
    print("=" * 60)
    print("MySelfAgent - LangChain Agent 演示")
    print("=" * 60)
    
    # 初始化组件
    print("\n[1] 初始化组件...")
    
    # LLM
    llm = LocalLLM(
        api_base="http://127.0.0.1:8788",
        api_path="/v1/responses",
        model_name="default"
    )
    print("  ✓ LLM 已初始化")
    
    # 工具注册
    tool_registry = ToolRegistry()
    tool_registry.register(PythonExecTool(timeout=10))
    tool_registry.register(FileIOTool(allowed_paths=[".", "./workspace"]))
    tool_registry.register(SearchTool())
    print("  ✓ 工具已注册:", [t.name for t in tool_registry.list_tools()])
    
    # 记忆系统
    memory = BufferMemory(max_size=50, persist_path="memory.json")
    print("  ✓ 记忆系统已初始化")
    
    # 规划器
    planner = SimplePlanner(max_steps=5)
    print("  ✓ 规划器已初始化")
    
    # 创建Agent
    agent = Agent(
        llm=llm,
        memory=memory,
        planner=planner,
        tool_registry=tool_registry,
        max_iterations=5
    )
    print("  ✓ Agent 已创建")
    
    # 运行示例
    print("\n[2] 运行示例任务...")
    goal = "创建一个简单的Python计算器"
    
    print(f"\n目标: {goal}")
    print("-" * 60)
    
    try:
        result = agent.run(goal)
        
        print("\n[3] 执行结果:")
        print(f"  目标: {result['goal']}")
        print(f"  迭代次数: {result['iterations']}")
        print(f"  计划状态: {result['plan_status']}")
        print(f"  进度: {result['progress']['progress']:.1%}")
        
        # 显示记忆摘要
        print("\n[4] 记忆摘要:")
        summary = agent.get_memory_summary()
        print(f"  总消息数: {summary.get('total_messages', 0)}")
        
    except Exception as e:
        print(f"\n错误: {e}")
        print("提示: 请确保本地API服务正在运行于 http://127.0.0.1:8788")
    
    print("\n" + "=" * 60)
    print("演示完成!")


if __name__ == "__main__":
    main()
