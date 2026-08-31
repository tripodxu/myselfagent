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
        debug=debug
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

    log_path = result.get('log_path')
    if log_path:
        lines.append(f"")
        lines.append(f"[日志已导出: {log_path}]")
    lines.append(f"")
    lines.append(f"[执行{result['iterations']}轮，状态: {result['plan_status']}，耗时{result.get('total_time', 0):.2f}秒]")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="MySelfAgent - LangChain Agent")
    parser.add_argument("goal", nargs="?", default=None, help="要执行的目标（可放在任意位置）")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    parser.add_argument("--debug", "-d", action="store_true", help="调试模式（自动导出日志）")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--export-log", "-e", action="store_true", help="导出日志（自动命名）")
    parser.add_argument("--log-path", "-l", type=str, default=None, help="指定日志文件路径")

    args = parser.parse_args()

    print("=" * 60)
    print("MySelfAgent v1.4.0 - LangChain Agent 系统")
    print("=" * 60)

    agent = create_agent(debug=args.debug)
    print(f"Agent 已初始化")
    print(f"LLM模型: {LLM_MODEL_NAME}")
    print(f"Stream: 已开启")
    print(f"API地址: {LLM_API_BASE}{LLM_API_PATH}")
    if args.debug:
        print(f"调试模式: 已开启")

    # Determine log export
    should_export = args.export_log or args.debug
    log_export_path = args.log_path  # None = auto-generate

    def do_export(result):
        if should_export:
            try:
                path = agent.export_logs(log_export_path)
                result['log_path'] = path
            except Exception as ex:
                print(f"\u65e5\u5fd7\u5bfc\u51fa\u5931\u8d25: {ex}")

    if args.goal:
        # Single goal mode (goal can be at any position)
        print("\n" + "-" * 60)
        result = agent.run(args.goal)
        do_export(result)
        print("-" * 60)
        print(format_result(result))
    elif args.interactive:
        print("\n\u8fdb\u5165\u4ea4\u4e92\u6a21\u5f0f (\u8f93\u5165 'quit' \u9000\u51fa)")
        while True:
            try:
                goal = input("\n\u8bf7\u8f93\u5165\u76ee\u6807: ").strip()
                if goal.lower() in ["quit", "exit", "q"]:
                    print("\u518d\u89c1\uff01")
                    break
                if not goal:
                    continue

                print("\n" + "-" * 60)
                result = agent.run(goal)
                do_export(result)
                print("-" * 60)
                print(format_result(result))

            except KeyboardInterrupt:
                print("\n\n\u518d\u89c1\uff01")
                break
            except EOFError:
                print("\n\n\u518d\u89c1\uff01")
                break
            except ValueError as e:
                if "I/O operation on closed file" in str(e):
                    print(f"\n[ERROR] \u8f93\u51fa\u6d41\u5df2\u5173\u95ed\uff0c\u65e0\u6cd5\u7ee7\u7eed: {e}")
                    break
                raise
    else:
        print("\n\u7528\u6cd5:")
        print("  python main.py '\u4f60\u7684\u95ee\u9898'               # \u5355\u6b21\u6267\u884c")
        print("  python main.py '\u95ee\u9898' -d -e           # \u6267\u884c+\u8c03\u8bd5+\u5bfc\u51fa\u65e5\u5fd7")
        print("  python main.py -d -e '\u95ee\u9898'           # \u540c\u4e0a\uff0c\u65e7\u540e\u4f4d\u7f6e\u53ef\u8c03")
        print("  python main.py -i -d -e                    # \u4ea4\u4e92\u6a21\u5f0f+\u8c03\u8bd5+\u65e5\u5fd7")
        print("  python main.py -e -l log.txt '\u95ee\u9898'       # \u6267\u884c+\u6307\u5b9a\u65e5\u5fd7\u8def\u5f84")


if __name__ == "__main__":
    main()
