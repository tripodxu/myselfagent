#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySelfAgent - 主入口
LangChain Agent 系统
"""

import os
# 设置环境变量，确保子进程也使用UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'

import argparse
import sys

# 修复Windows编码问题 - 使用reconfigure()就地修改，避免替换stream对象
# 替换stream会导致旧对象被GC时关闭底层fd，引发"I/O operation on closed file"
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        # 不要reconfigure stdin - input()需要原始console stream
    except AttributeError:
        # Python < 3.7 fallback（不太可能，但防御性编程）
        import io
        _orig_stdout = sys.stdout
        _orig_stderr = sys.stderr
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from src.llm import LocalLLM
from src.tools.base import ToolRegistry
from src.tools.python_exec import PythonExecTool
from src.tools.file_io import FileIOTool
from src.tools.search import SearchTool
from src.tools.datetime_tool import DateTimeTool
from src.memory.buffer import BufferMemory
from src.planner.llm_planner import LLMPlanner
from src.agent import Agent
from config import (
    LLM_API_BASE, LLM_API_PATH, LLM_MODEL_NAME,
    LLM_TIMEOUT, LLM_MAX_RETRIES,
    PYTHON_EXEC_TIMEOUT, FILE_IO_ALLOWED_PATHS,
    MEMORY_CONTEXT_WINDOW, MEMORY_PERSIST_PATH,
    PLANNER_MAX_STEPS
)


def create_agent(debug: bool = False) -> Agent:
    llm = LocalLLM(
        api_base=LLM_API_BASE,
        api_path=LLM_API_PATH,
        model_name=LLM_MODEL_NAME,
        timeout=LLM_TIMEOUT,
        max_retries=LLM_MAX_RETRIES,
        debug=debug,
        use_stream=True
    )

    tool_registry = ToolRegistry()
    tool_registry.register(PythonExecTool(timeout=PYTHON_EXEC_TIMEOUT))
    tool_registry.register(FileIOTool(allowed_paths=FILE_IO_ALLOWED_PATHS))
    tool_registry.register(SearchTool())
    tool_registry.register(DateTimeTool())

    memory = BufferMemory(max_size=MEMORY_CONTEXT_WINDOW * 10, persist_path=MEMORY_PERSIST_PATH)
    planner = LLMPlanner(llm=llm, max_steps=PLANNER_MAX_STEPS)

    return Agent(
        llm=llm,
        memory=memory,
        planner=planner,
        tool_registry=tool_registry,
        max_iterations=PLANNER_MAX_STEPS,
        debug=debug,
        use_stream=True
    )


def format_result(result: dict) -> str:
    lines = []

    final = result.get("final_result")
    if final:
        if final.get("date"):
            lines.append(f"日期: {final['date']}")
        if final.get("time"):
            lines.append(f"时间: {final['time']}")
        if final.get("datetime"):
            lines.append(f"日期时间: {final['datetime']}")
        if final.get("weekday"):
            lines.append(f"星期: {final['weekday']}")
        if final.get("output"):
            output = final['output']
            if isinstance(output, bytes):
                output = output.decode('utf-8', errors='replace')
            lines.append(f"输出: {output.strip()}")
        if final.get("content"):
            lines.append(f"内容: {final['content']}")
        if final.get("result"):
            lines.append(f"结果: {final['result']}")

    if not lines and final:
        lines.append(f"结果: {final}")

    lines.append(f"")
    lines.append(f"[执行{result['iterations']}轮，状态: {result['plan_status']}，耗时{result.get('total_time', 0):.2f}秒]")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="MySelfAgent - LangChain Agent")
    parser.add_argument("goal", nargs="?", help="要执行的目标")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    parser.add_argument("--debug", "-d", action="store_true", help="调试模式")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    print("=" * 60)
    print("MySelfAgent - LangChain Agent 系统")
    print("=" * 60)

    agent = create_agent(debug=args.debug)
    print(f"Agent 已初始化")
    print(f"LLM模型: {LLM_MODEL_NAME}")
    print(f"Stream: 已开启")
    print(f"API地址: {LLM_API_BASE}{LLM_API_PATH}")
    if args.debug:
        print(f"调试模式: 已开启")

    if args.interactive:
        print("\n进入交互模式 (输入 'quit' 退出)")
        while True:
            try:
                goal = input("\n请输入目标: ").strip()
                if goal.lower() in ["quit", "exit", "q"]:
                    print("再见！")
                    break
                if not goal:
                    continue

                print("\n" + "-" * 60)
                result = agent.run(goal)
                print("-" * 60)
                print(format_result(result))

            except KeyboardInterrupt:
                print("\n\n再见！")
                break
            except EOFError:
                print("\n\n再见！")
                break
            except ValueError as e:
                if "I/O operation on closed file" in str(e):
                    print(f"\n[ERROR] 输出流已关闭，无法继续: {e}")
                    break
                raise
    elif args.goal:
        result = agent.run(args.goal)
        print("\n" + format_result(result))
    else:
        print("\n用法:")
        print("  python main.py '你的问题'")
        print("  python main.py --interactive")
        print("  python main.py --interactive --debug")


if __name__ == "__main__":
    main()
