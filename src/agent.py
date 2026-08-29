import json
import re
import time
from typing import Any, Dict, List, Optional
from datetime import datetime
from .llm import LocalLLM
from .tools.base import BaseTool, ToolRegistry
from .memory.base import BaseMemory
from .planner.llm_planner import LLMPlanner


def get_timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


# Safety: dangerous tool patterns that need extra review
DANGEROUS_PATTERNS = [
    "rm -rf", "rmdir /s", "del /f",
    "format c:", "shutdown",
    "import subprocess", "import shutil", "import socket",
    "os.system(", "os.popen(",
]


def has_answer(result: dict) -> bool:
    if not result.get("success"):
        return False
    output = result.get("output", "")
    if output and len(str(output).strip()) > 0:
        stripped = str(output).strip()
        fallback_markers = ["exec step:", "step done:", "step complete:"]
        if any(marker in stripped.lower() for marker in fallback_markers):
            return False
        return True
    if result.get("date") or result.get("time") or result.get("weekday") or result.get("datetime"):
        return True
    if result.get("content"):
        return True
    if result.get("result"):
        return True
    return False


def select_best_result(step_results: list) -> dict:
    successful = [r for r in step_results if r.get("result", {}).get("success")]
    if not successful:
        return {}
    with_answer = [r for r in successful if has_answer(r["result"])]
    if with_answer:
        with_output = [r for r in with_answer if r["result"].get("output")]
        if with_output:
            return with_output[-1]["result"]
        return with_answer[-1]["result"]
    return successful[-1]["result"]


class Agent:
    def __init__(
        self,
        llm: LocalLLM = None,
        memory: BaseMemory = None,
        planner: LLMPlanner = None,
        tool_registry: ToolRegistry = None,
        max_iterations: int = 10,
        debug: bool = False
    ):
        self.llm = llm or LocalLLM()
        self.memory = memory
        self.planner = planner or LLMPlanner(llm=self.llm)
        self.tool_registry = tool_registry or ToolRegistry()
        self.max_iterations = max_iterations
        self.iteration = 0
        self.debug = debug
        self.debug_logs = []

    def log(self, message: str, level: str = "INFO"):
        timestamp = get_timestamp()
        log_entry = f"[{timestamp}] [{level}] {message}"
        if self.debug:
            try:
                print(log_entry, flush=True)
            except (UnicodeEncodeError, ValueError):
                pass
        self.debug_logs.append({"timestamp": timestamp, "level": level, "message": message})

    # === Safety Review Layer ===
    def _check_safety(self, decision: dict) -> dict:
        """Review tool call for safety before execution."""
        tool_name = decision.get("tool", "")
        params = decision.get("params", {})

        # Check all string params for dangerous patterns
        for key, val in params.items():
            if isinstance(val, str):
                for pattern in DANGEROUS_PATTERNS:
                    if pattern.lower() in val.lower():
                        self.log(f"Safety block: {pattern} in {key}", "SAFETY")
                        return {"safe": False, "reason": f"Blocked: contains '{pattern}'"}

        # Check if tool exists
        if not self.tool_registry.has_tool(tool_name):
            return {"safe": False, "reason": f"Unknown tool: {tool_name}"}

        return {"safe": True, "reason": "ok"}

    # === Message Builder (layered like Codex) ===
    def _build_messages(self, goal: str, step_desc: str, prior_results: list) -> list:
        """Build layered messages: developer -> user -> assistant history -> tool results."""
        messages = []

        # Layer 1: Developer instructions (system rules)
        tool_defs = self.tool_registry.get_tool_definitions()
        tools_text = json.dumps(tool_defs, ensure_ascii=False, indent=2)
        developer_content = (
            "You are an AI agent that selects tools to accomplish tasks.\n"
            "Rules:\n"
            "1. Return ONLY a JSON object with tool name and params\n"
            "2. Use python_exec for multi-step tasks (create file + run)\n"
            "3. If previous steps already completed the goal, do NOT call more tools\n\n"
            f"Available tools (JSON Schema):\n{tools_text}\n\n"
            "Output format:\n"
            '{"tool": "tool_name", "params": {"key": "value"}}'
        )
        messages.append({"role": "developer", "content": developer_content})

        # Layer 2: User request (goal + current step)
        user_content = f"Goal: {goal}\nCurrent step: {step_desc}"
        messages.append({"role": "user", "content": user_content})

        # Layer 3: Previous tool results (as assistant context)
        if prior_results:
            history_lines = []
            for pr in prior_results[-3:]:
                r = pr["result"]
                if r.get("success"):
                    summary = r.get("output", "").strip()[:200] or r.get("message", "")[:200]
                    history_lines.append(f"Step {pr['step']}: {pr['tool']} -> {summary}")
                else:
                    err_msg = r.get("error", "unknown")[:100]
                    history_lines.append(f"Step {pr['step']}: {pr['tool']} -> FAILED: {err_msg}")
            messages.append({"role": "assistant", "content": "Previous results:\n" + "\n".join(history_lines)})

        return messages

    def run(self, goal: str) -> Dict[str, Any]:
        self.iteration = 0
        self.debug_logs = []
        step_results = []
        start_time = time.time()

        self.log(f"Goal: {goal}", "GOAL")
        self.log(f"Max iterations: {self.max_iterations}", "CONFIG")

        # Auto-adjust reasoning effort based on goal complexity
        effort = self._estimate_complexity(goal)
        self.llm.set_reasoning_effort(effort)
        self.log(f"Reasoning effort: {effort}", "CONFIG")

        # Phase 1: LLM decomposes goal into plan
        self.log("Creating plan with LLM...", "PLAN")
        plan = self.planner.create_plan(goal)
        plan_id = list(self.planner.plans.keys())[-1]
        progress = self.planner.get_plan_progress(plan_id)
        self.log(f"Plan created: {progress['total_steps']} steps", "PLAN")
        for i, s in enumerate(plan.steps):
            self.log(f"  Step {i+1}: {s.description}", "PLAN")

        if self.memory:
            self.memory.add_message("system", f"Goal: {goal}")

        # Phase 2: Execute plan with feedback loop
        while self.iteration < self.max_iterations:
            self.iteration += 1
            iter_start = time.time()

            next_step = self.planner.get_next_step(plan_id)
            if not next_step:
                self.log("No more steps", "PLAN")
                break

            self.log(f"Iter {self.iteration}: Step {next_step.id} - {next_step.description}", "ITER")

            # Decide
            self.log("Deciding...", "DECIDE")
            decision_start = time.time()
            decision = self._make_decision(next_step.description, goal, step_results)
            decision_time = time.time() - decision_start
            self.log(f"Decision: {decision_time:.2f}s", "DECIDE")
            self.log(f"Tool: {decision.get('tool')}", "TOOL")

            # Safety review
            safety = self._check_safety(decision)
            self.log(f"Safety: {safety['reason']}", "SAFETY")
            if not safety["safe"]:
                result = {"success": False, "error": safety["reason"]}
                step_results.append({"step": self.iteration, "description": next_step.description,
                                     "tool": decision.get("tool"), "result": result})
                self.planner.mark_step_failed(plan_id, next_step.id, safety["reason"])
                continue

            # Execute
            self.log("Executing...", "EXEC")
            exec_start = time.time()
            result = self._execute_decision(decision)
            exec_time = time.time() - exec_start
            self.log(f"Executed: {exec_time:.2f}s", "EXEC")

            try:
                result_str = json.dumps(result, ensure_ascii=False)[:300]
            except (TypeError, ValueError):
                result_str = str(result)[:300]
            self.log(f"Result: {result_str}", "RESULT")

            step_results.append({"step": self.iteration, "description": next_step.description,
                                 "tool": decision.get("tool"), "result": result,
                                 "decision_time": decision_time, "exec_time": exec_time})

            if self.memory:
                self.memory.add_message("assistant", f"Step {self.iteration}: {result_str}")

            if result.get("success", False):
                self.planner.mark_step_completed(plan_id, next_step.id, result)
            else:
                self.planner.mark_step_failed(plan_id, next_step.id, result.get("error"))

            iter_time = time.time() - iter_start
            self.log(f"Iter {self.iteration} done: {iter_time:.2f}s", "ITER")

            if has_answer(result):
                self.log("Answer found, stopping", "DONE")
                break

            # Evaluate
            self.log("Evaluating...", "EVAL")
            evaluation = self.planner.evaluate_result(plan_id, next_step.id, result, goal)
            action = evaluation.get("action", "continue")
            reason = evaluation.get("reason", "")
            self.log(f"Eval: {action} - {reason}", "EVAL")

            if action == "stop":
                self.log("LLM says stop", "DONE")
                break
            elif action == "replan":
                new_steps = evaluation.get("new_steps", [])
                if new_steps:
                    self.log(f"Replanning: {len(new_steps)} steps", "PLAN")
                    self.planner.replan(plan_id, new_steps)

        final_result = select_best_result(step_results)
        total_time = time.time() - start_time
        self.log(f"Done: {total_time:.2f}s, {self.iteration} iters", "DONE")

        self.planner.mark_plan_completed(plan_id)
        progress = self.planner.get_plan_progress(plan_id)

        return {"goal": goal, "iterations": self.iteration, "plan_status": "completed",
                "final_result": final_result, "step_results": step_results,
                "total_time": total_time, "progress": progress}

    def _make_decision(self, step_desc: str, goal: str, prior_results: list = None) -> Dict[str, Any]:
        messages = self._build_messages(goal, step_desc, prior_results or [])
        prompt = "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in messages)

        # Log each layer separately for debugging
        for m in messages:
            self.log(f"[{m['role'].upper()}] {m['content'][:300]}", "MSG")

        self.log(f"Full prompt sent to LLM", "API_REQ")

        tools = self.tool_registry.list_tools()
        tool_names = [t.name for t in tools]

        try:
            response = self.llm._call(prompt)
            self.log(f"LLM response: {response[:300]}", "API_RES")
            decision = self._parse_json(response)
            if decision:
                return decision
            raise json.JSONDecodeError("No valid JSON", response, 0)
        except Exception as e:
            self.log(f"Decision failed: {e}", "ERROR")
            return {"tool": tool_names[0] if tool_names else "python_exec",
                    "params": {"code": f"print('step done: {step_desc}')"}}

    def _estimate_complexity(self, goal: str) -> str:
        """Estimate task complexity for reasoning effort control."""
        simple_keywords = ["date", "time", "weekday", "today", "tomorrow", "yesterday"]
        complex_keywords = ["create", "build", "implement", "design", "analyze", "debug", "refactor"]

        goal_lower = goal.lower()
        if any(kw in goal_lower for kw in simple_keywords):
            return "low"
        if any(kw in goal_lower for kw in complex_keywords):
            return "high"
        return "medium"

    def _parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = text[json_start:json_end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
            fixed = json_str.replace("\\n", "\n").replace("\\t", "\t")
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass
            tool_match = re.search(r"\"tool\"\s*:\s*\"([^\"]+)\"", json_str)
            if tool_match:
                tool_name = tool_match.group(1)
                params = {}
                for key in ["action", "path"]:
                    km = re.search(rf"\"{key}\"\s*:\s*\"([^\"]+)\"", json_str)
                    if km:
                        params[key] = km.group(1)
                for key in ["content", "code"]:
                    km = re.search(rf"\"{key}\"\s*:\s*\"((?:[^\"\\]|\\.)*)\"", json_str, re.DOTALL)
                    if km:
                        val = km.group(1).replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\\\", "\\")
                        params[key] = val
                return {"tool": tool_name, "params": params}
        return None

    def _execute_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = decision.get("tool")
        params = decision.get("params", {})
        if not tool_name:
            return {"success": False, "error": "no tool specified"}
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            return {"success": False, "error": f"tool not found: {tool_name}"}
        try:
            result = tool.execute(**params)
            return result if isinstance(result, dict) else {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_memory_summary(self) -> Dict[str, Any]:
        if self.memory:
            return self.memory.get_summary()
        return {"error": "no memory configured"}
