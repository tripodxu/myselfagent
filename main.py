#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySelfAgent - 主入口
LangChain Agent 系统
"""

import argparse
import sys
import os

from src.llm import LocalLLM
from src.tools.base import ToolRegistry
from src.tools.python_exec import PythonExecTool
from src.tools.file_io import FileIOTool
from src.tools.search import SearchTool
from src.tools.datetime_tool import DateTimeTool
from src.memory.buffer import BufferMemory
from src.planner.simple import SimplePlanner
from src.agent import Agent
from config import (
    LLM_API_BASE, LLM_API_PATH, LLM_MODEL_NAME,
    LLM_TIMEOUT, LLM_MAX_RETRIES,
    PYTHON_EXEC_TIMEOUT, FILE_IO_ALLOWED_PATHS,
    MEMORY_CONTEXT_WINDOW, MEMORY_PERSIST_PATH,
    PLANNER_MAX_STEPS
)


def create_agent() -> Agent:
    """"创建Agent实例"""
    # 初始化LLM
    llm = LocalLLM(
        api_base=LLM_API_BASE,
        api_path=LLM_API_PATH,
        model_name=LLM_MODEL_NAME,
        timeout=LLM_TIMEOUT,
        max_retries=LLM_MAX_RETRIES
    )
    
    # 注册工具
    tool_registry = ToolRegistry()
    tool_registry.register(PythonExecTool(timeout=PYTHON_EXEC_TIMEOUT))
    tool_registry.register(FileIOTool(allowed_paths=FILE_IO_ALLOWED_PATHS))
    tool_registry.register(SearchTool())
    tool_registry.register(DateTimeTool())
    
    # 初始化记忆
    memory = BufferMemory(
        max_size=MEMORY_CONTEXT_WINDOW * 10,
        persist_path=MEMORY_PERSIST_PATH
    )
    
    # 初始化规划器
    planner = SimplePlanner(max_steps=PLANNER_MAX_STEPS)
    
    # 创建Agent
    return Agent(
        llm=llm,
        memory=memory,
        planner=planner,
        tool_registry=tool_registry,
        max_iterations=PLANNER_MAX_STEPS
    )


def main():
    parser = argparse.ArgumentParser(description="MySelfAgent - LangChain Agent")
    parser.add_argument("goal", nargs="?", help="要执行的目标")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MySelfAgent - LangChain Agent 系统")
    print("=" * 60)
    
    agent = create_agent()
    print("Agent 已初始化")
    print(f"LLM模型: {LLM_MODEL_NAME}")
    print(f"API地址: {LLM_API_BASE}{LLM_API_PATH}")
    
    if args.interactive:
        # 交互模式
        print("\n进入交互模式 (输入 'quit' 退出)")
        while True:
            try:
                goal = input("\n请输入目标: ").strip()
                if goal.lower() in ["quit", "exit", "q"]:
                    break
                if not goal:
                    continue
                
                result = agent.run(goal)
                print(f"\n结果: {result}")
                
            except KeyboardInterrupt:
                print("\n\n退出...")
                break
    elif args.goal:
        # 单次执行
        result = agent.run(args.goal)
        print(f"\n执行结果:")
        print(f"  目标: {result['goal']}")
        print(f"  迭代次数: {result['iterations']}")
        print(f"  计划状态: {result['plan_status']}")
        print(f"  进度: {result['progress']['progress']:.1%}")
    else:
        # 默认运行演示
        from examples.demo import main as demo_main
        demo_main()


if __name__ == "__main__":
    main()
