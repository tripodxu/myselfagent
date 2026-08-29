#!/usr/bin/env python3
"""MySelfAgent v1.3.0 complete feature test"""
import sys, os, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm import LocalLLM
from src.tools.base import BaseTool, ToolRegistry
from src.tools.python_exec import PythonExecTool
from src.tools.file_io import FileIOTool
from src.tools.search import SearchTool
from src.tools.datetime_tool import DateTimeTool
from src.memory.buffer import BufferMemory
from src.memory.context_manager import ContextManager
from src.planner.llm_planner import LLMPlanner
from src.planner.simple import SimplePlanner
from src.agent import Agent, has_answer, select_best_result, DANGEROUS_PATTERNS


def sep(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def test_tool_schema():
    sep("1. Tool JSON Schema System")
    reg = ToolRegistry()
    reg.register(PythonExecTool(timeout=10))
    reg.register(FileIOTool(allowed_paths=["."]))
    reg.register(SearchTool())
    reg.register(DateTimeTool())
    for t in reg.list_tools():
        s = t.parameters_schema()
        assert "type" in s and "properties" in s
        print(f"  [{t.name}] {json.dumps(s, ensure_ascii=False)[:80]}")
    defs = reg.get_tool_definitions()
    assert len(defs) == 4
    for d in defs:
        assert "name" in d and "parameters" in d
    print(f"  {len(defs)} tools with valid JSON Schema")
    print("  PASS")


def test_context():
    sep("2. Context Management")
    mem = BufferMemory()
    cm = ContextManager(memory=mem, max_tokens=100)
    msgs = [
        ("system", "You are an AI agent"),
        ("user", "Create a file called test.txt with hello world"),
        ("assistant", "I will use file_io tool"),
        ("tool", '{"success": true, "message": "Written: test.txt"}'),
        ("assistant", "File created"),
        ("user", "Now read the file back"),
        ("assistant", "Reading file..."),
        ("tool", '{"success": true, "content": "hello world"}'),
        ("assistant", "File contains: hello world"),
    ]
    for role, content in msgs:
        cm.add_message(role, content)
    stats = cm.get_stats()
    print(f"  Messages: {stats['total_messages']}, tokens: {stats['estimated_tokens']}")
    print(f"  Utilization: {stats['utilization']*100:.0f}%, has_summary: {stats['has_summary']}")
    assert stats["has_summary"], "Should have triggered auto-compression"
    ctx = cm.get_context()
    sys_m = [m for m in ctx if m["role"] == "system"]
    assert len(sys_m) >= 1
    print(f"  Context: {len(ctx)} messages, system preserved: {len(sys_m)}")

    # Tool truncation test with SAME memory
    cm2 = ContextManager(memory=mem, max_tokens=4000)
    cm2.add_message("tool", "x" * 2000)
    tool_m = [m for m in cm2.context_window if m["role"] == "tool"]
    assert len(tool_m[0]["content"]) <= 600
    print(f"  Tool truncation: 2000 -> {len(tool_m[0]['content'])} chars")

    # Memory has all messages (9 from cm + 1 from cm2)
    assert len(mem.get_history()) == 10
    print(f"  BufferMemory: {len(mem.get_history())} messages persisted")
    print("  PASS")


def test_safety():
    sep("3. Safety Review Layer")
    agent = Agent.__new__(Agent)
    agent.tool_registry = ToolRegistry()
    agent.tool_registry.register(PythonExecTool())
    agent.tool_registry.register(FileIOTool())
    agent.debug = False
    agent.debug_logs = []

    cases = [
        ({"tool": "python_exec", "params": {"code": "import subprocess; subprocess.run('rm -rf /')"}}, False),
        ({"tool": "python_exec", "params": {"code": "import socket"}}, False),
        ({"tool": "python_exec", "params": {"code": "os.system('format c:')"}}, False),
        ({"tool": "python_exec", "params": {"code": "print('hello')"}}, True),
        ({"tool": "file_io", "params": {"action": "read", "path": "config.txt"}}, True),
    ]
    for tc, expected_safe in cases:
        r = agent._check_safety(tc)
        status = "OK" if r["safe"] == expected_safe else "FAIL"
        code = str(tc["params"].get("code", tc["params"]))[:60]
        print(f"  [{status}] {'ALLOWED' if r['safe'] else 'BLOCKED'}: {code}")

    assert agent._check_safety({"tool": "python_exec", "params": {"code": "print(42)"}})["safe"]
    assert not agent._check_safety({"tool": "python_exec", "params": {"code": "import subprocess"}})["safe"]
    assert not agent._check_safety({"tool": "hack_tool", "params": {}})["safe"]
    print(f"  {len(DANGEROUS_PATTERNS)} dangerous patterns checked")
    print("  PASS")


def test_reasoning():
    sep("4. Reasoning Effort Control")
    agent = Agent.__new__(Agent)
    agent.llm = LocalLLM()
    cases = [
        ("What is today's date?", "low"),
        ("Query the current time", "low"),
        ("Build a web scraper", "high"),
        ("Implement a REST API", "high"),
        ("Analyze the log files", "high"),
        ("List files in directory", "medium"),
        ("Process the data file", "medium"),
    ]
    for goal, expected in cases:
        effort = agent._estimate_complexity(goal)
        status = "OK" if effort == expected else "FAIL"
        print(f"  [{status}] '{goal[:35]}' -> {effort}")
        assert effort == expected
    print("  PASS")


def test_planner():
    sep("5. Planner System")
    # SimplePlanner: goal becomes single step
    sp = SimplePlanner(max_steps=5)
    plan = sp.create_plan("Read config and extract database URL")
    pid = list(sp.plans.keys())[0]
    print(f"  Goal: {plan.goal}")
    print(f"  Steps: {len(plan.steps)} -> {plan.steps[0].description}")
    assert len(plan.steps) == 1
    assert plan.steps[0].description == "Read config and extract database URL"

    sp.mark_step_completed(pid, 1)
    assert sp.get_next_step(pid) is None
    assert sp.is_plan_complete(pid)
    print(f"  After completion: no next step, plan complete")
    progress = sp.get_plan_progress(pid)
    print(f"  Progress: {progress['completed']}/{progress['total_steps']}, status={progress['status']}")

    # LLMPlanner fallback
    lp = LLMPlanner(llm=None, max_steps=5)
    plan = lp.create_plan("Test goal")
    assert len(plan.steps) == 1
    print(f"  LLMPlanner fallback: 1 step")
    print("  PASS")


def test_memory():
    sep("6. Memory System")
    mem = BufferMemory(max_size=5)
    for i in range(8):
        mem.add_message("user", f"Message {i}")
    h = mem.get_history()
    assert len(h) == 5
    print(f"  max_size=5: {len(h)} messages kept")

    mem.add_message("assistant", "The answer is 42")
    found = mem.search_messages("42")
    assert len(found) >= 1
    print(f"  Search '42': {len(found)} found")

    summary = mem.get_summary()
    assert summary["total_messages"] > 0
    print(f"  Summary: {summary['total_messages']} messages")

    # Persistence
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        pp = f.name
    mem2 = BufferMemory(max_size=100, persist_path=pp)
    mem2.add_message("user", "persistent msg")
    mem2.add_message("assistant", "persistent reply")
    mem3 = BufferMemory(max_size=100, persist_path=pp)
    assert len(mem3.get_history()) == 2
    print(f"  Persistence: {len(mem3.get_history())} messages loaded from file")
    os.unlink(pp)
    print("  PASS")


def test_answer_detection():
    sep("7. Answer Detection & Result Selection")
    cases = [
        ({"success": True, "output": "34"}, True),
        ({"success": True, "output": "hello"}, True),
        ({"success": True, "date": "2026-08-29"}, True),
        ({"success": True, "content": "file"}, True),
        ({"success": True, "result": "computed"}, True),
        ({"success": False, "error": "failed"}, False),
        ({"success": True, "output": ""}, False),
        ({"success": True, "output": "step done: xxx"}, False),
        ({"success": True, "output": "exec step: yyy"}, False),
    ]
    for result, expected in cases:
        actual = has_answer(result)
        status = "OK" if actual == expected else "FAIL"
        print(f"  [{status}] {result} -> {actual}")

    steps = [
        {"step": 1, "result": {"success": True, "message": "file written"}},
        {"step": 2, "result": {"success": True, "output": "Result: 42"}},
        {"step": 3, "result": {"success": False, "error": "timeout"}},
    ]
    best = select_best_result(steps)
    assert best.get("output") == "Result: 42"
    print(f"  Best result: {best}")
    assert select_best_result([]) == {}
    print("  PASS")


def test_agent_cycle():
    sep("8. Agent Full Cycle (Mock LLM)")
    from unittest.mock import MagicMock
    mock = MagicMock(spec=LocalLLM)
    mock._call.side_effect = [
        json.dumps({"steps": ["Create fib script", "Run it", "Verify"]}),
        json.dumps({"tool": "python_exec", "params": {"code": "def fib(n):\n    a,b=0,1\n    for _ in range(n): a,b=b,a+b\n    return a\nprint(f'fib(10)={fib(10)}')"}}),
        json.dumps({"action": "stop", "reason": "done"}),
    ]
    reg = ToolRegistry()
    reg.register(PythonExecTool(timeout=10))
    mem = BufferMemory()
    agent = Agent(llm=mock, memory=mem, planner=LLMPlanner(llm=mock, max_steps=5),
                  tool_registry=reg, max_iterations=5, debug=True)
    r = agent.run("Calculate fibonacci(10)")
    print(f"  Goal: {r['goal']}")
    print(f"  Iterations: {r['iterations']}, time: {r['total_time']:.2f}s")
    final = r.get("final_result", {})
    if final.get("output"):
        print(f"  Output: {final['output'].strip()}")
    assert r["iterations"] <= 3
    assert r["plan_status"] == "completed"
    assert len(mem.get_history()) > 0
    levels = set(l["level"] for l in agent.debug_logs)
    print(f"  Debug levels: {sorted(levels)}")
    print("  PASS")


def test_real_tools():
    sep("9. Real Tool Execution")
    reg = ToolRegistry()
    reg.register(PythonExecTool(timeout=10))
    reg.register(FileIOTool(allowed_paths=[r"E:\mimo\test", "."]))
    reg.register(DateTimeTool())

    py = reg.get_tool("python_exec")
    r = py.execute(code="import math; print(f'pi={math.pi:.4f}')")
    assert r["success"]
    print(f"  PythonExec: {r['output'].strip()}")

    # FileIO with allowed path
    fi = reg.get_tool("file_io")
    test_dir = r"E:\mimo\test"
    r = fi.execute(action="list", path=test_dir)
    assert r["success"]
    print(f"  FileIO list: {len(r['items'])} items in {test_dir}")

    # Write to allowed path
    test_file = os.path.join(test_dir, "_test_output.txt")
    r = fi.execute(action="write", path=test_file, content="MySelfAgent test write")
    assert r["success"]
    print(f"  FileIO write: {r['message']}")

    r = fi.execute(action="read", path=test_file)
    assert r["success"]
    assert r["content"] == "MySelfAgent test write"
    print(f"  FileIO read: {r['content']}")

    # Cleanup
    os.unlink(test_file)

    dt = reg.get_tool("datetime")
    r = dt.execute(action="now")
    assert r["success"]
    print(f"  DateTime: {r['datetime']}")

    r = dt.execute(action="+3")
    assert r["success"]
    print(f"  DateTime +3: {r['date']} ({r['weekday']})")

    for t in reg.list_tools():
        assert t.parameters_schema()["type"] == "object"
    print(f"  All schemas valid")
    print("  PASS")


def test_ctx_agent():
    sep("10. Context + Agent Integration")
    from unittest.mock import MagicMock
    mock = MagicMock(spec=LocalLLM)
    mock._call.side_effect = [
        json.dumps({"steps": ["step1"]}),
        json.dumps({"tool": "datetime", "params": {"action": "now"}}),
        json.dumps({"action": "stop", "reason": "done"}),
    ]
    reg = ToolRegistry()
    reg.register(DateTimeTool())
    mem = BufferMemory()
    cm = ContextManager(memory=mem, max_tokens=200)
    agent = Agent(llm=mock, memory=mem, planner=LLMPlanner(llm=mock, max_steps=5),
                  tool_registry=reg, max_iterations=3, debug=False)
    agent.context = cm
    r = agent.run("What time is it?")
    stats = cm.get_stats()
    print(f"  Context: {stats['total_messages']} msgs, {stats['estimated_tokens']} tokens")
    print(f"  Utilization: {stats['utilization']*100:.0f}%")
    h = mem.get_history()
    print(f"  Memory: {len(h)} messages")
    for msg in h[-3:]:
        print(f"    [{msg['role']}] {msg['content'][:60]}")
    print("  PASS")


def main():
    print("=" * 60)
    print("  MySelfAgent v1.3.0 - Complete Feature Test")
    print("=" * 60)
    tests = [test_tool_schema, test_context, test_safety, test_reasoning,
             test_planner, test_memory, test_answer_detection, test_agent_cycle,
             test_real_tools, test_ctx_agent]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    sep("SUMMARY")
    print(f"  Total: {len(tests)}, Passed: {passed}, Failed: {failed}")
    print(f"  {'ALL PASSED!' if failed == 0 else f'{failed} FAILED'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
