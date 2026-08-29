import json
import re
import sys
import time
from typing import Any, Dict, List, Optional
from datetime import datetime
from .llm import LocalLLM
from .tools.base import BaseTool, ToolRegistry
from .memory.base import BaseMemory
from .planner.llm_planner import LLMPlanner


def get_timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


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

    def run(self, goal: str) -> Dict[str, Any]:
        self.iteration = 0
        self.debug_logs = []
        step_results = []
        start_time = time.time()

        self.log(f"Goal: {goal}", "GOAL")
        self.log(f"Max iterations: {self.max_iterations}", "CONFIG")

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

            # Get next step from plan
            next_step = self.planner.get_next_step(plan_id)
            if not next_step:
                self.log("No more steps in plan", "PLAN")
                break

            self.log(f"Iteration {self.iteration}: Step {next_step.id} - {next_step.description}", "ITER")

            # Decide: choose tool based on goal + current step + prior results
            self.log("Deciding...", "DECIDE")
            decision_start = time.time()
            decision = self._make_decision(next_step.description, goal, step_results)
            decision_time = time.time() - decision_start
            self.log(f"Decision made in {decision_time:.2f}s", "DECIDE")
            self.log(f"Tool: {decision.get('tool')}", "TOOL")

            # Execute tool
            self.log("Executing...", "EXEC")
            exec_start = time.time()
            result = self._execute_decision(decision)
            exec_time = time.time() - exec_start
            self.log(f"Executed in {exec_time:.2f}s", "EXEC")

            try:
                result_str = json.dumps(result, ensure_ascii=False)[:300]
            except (TypeError, ValueError):
                result_str = str(result)[:300]
            self.log(f"Result: {result_str}", "RESULT")

            step_results.append({
                "step": self.iteration,
                "description": next_step.description,
                "tool": decision.get("tool"),
                "result": result,
                "decision_time": decision_time,
                "exec_time": exec_time
            })

            if self.memory:
                self.memory.add_message("assistant", f"Step {self.iteration}: {result_str}")

            # Mark step completed in planner
            if result.get("success", False):
                self.planner.mark_step_completed(plan_id, next_step.id, result)
            else:
                self.planner.mark_step_failed(plan_id, next_step.id, result.get("error"))

            iter_time = time.time() - iter_start
            self.log(f"Iteration {self.iteration} done in {iter_time:.2f}s", "ITER")

            # Early exit: if we have a concrete answer, stop
            if has_answer(result):
                self.log("Answer detected, stopping", "DONE")
                break

            # Phase 3: Evaluate result with LLM - should we continue/stop/replan?
            self.log("Evaluating result with LLM...", "EVAL")
            evaluation = self.planner.evaluate_result(
                plan_id,
                step_id=next_step.id,
                result=result,
                goal=goal
            )
            action = evaluation.get("action", "continue")
            reason = evaluation.get("reason", "")
            self.log(f"Evaluation: {action} - {reason}", "EVAL")

            if action == "stop":
                self.log("LLM says goal achieved, stopping", "DONE")
                break
            elif action == "replan":
                new_steps = evaluation.get("new_steps", [])
                if new_steps:
                    self.log(f"Replanning with {len(new_steps)} new steps", "PLAN")
                    self.planner.replan(plan_id, new_steps)
                    for i, s in enumerate(new_steps):
                        self.log(f"  New step: {s}", "PLAN")
                else:
                    self.log("Replan requested but no new steps, stopping", "DONE")
                    break

        # Select best result
        final_result = select_best_result(step_results)
        total_time = time.time() - start_time
        self.log(f"Done in {total_time:.2f}s, {self.iteration} iterations", "DONE")

        self.planner.mark_plan_completed(plan_id)
        progress = self.planner.get_plan_progress(plan_id)

        return {
            "goal": goal,
            "iterations": self.iteration,
            "plan_status": "completed",
            "final_result": final_result,
            "step_results": step_results,
            "total_time": total_time,
            "progress": progress
        }

    def _make_decision(self, step_desc: str, goal: str, prior_results: list = None) -> Dict[str, Any]:
        tools = self.tool_registry.list_tools()
        tool_names = [t.name for t in tools]

        tool_descriptions = []
        for tool in tools:
            desc = f"- {tool.name}: {tool.description}"
            if tool.name == "datetime":
                desc += "\n  params: action (now/date/time/weekday/tomorrow/yesterday/+N/-N)"
            elif tool.name == "python_exec":
                desc += "\n  params: code (Python code string)"
            elif tool.name == "file_io":
                desc += "\n  params: action (read/write/list), path, content"
            elif tool.name == "search":
                desc += "\n  params: action (text/file/files), pattern, text/target"
            tool_descriptions.append(desc)

        prompt = f"Goal: {goal}\n"
        prompt += f"Current step: {step_desc}\n\n"

        if prior_results:
            prompt += "Previous results:\n"
            for pr in prior_results[-3:]:
                r = pr["result"]
                if r.get("success"):
                    summary = r.get("output", "").strip()[:200] or r.get("message", "")[:200] or json.dumps(r, ensure_ascii=False)[:200]
                    prompt += f"- Step {pr['step']}: {pr['tool']} -> {summary}\n"
                else:
                    prompt += f"- Step {pr['step']}: {pr['tool']} -> FAILED: {r.get('error', 'unknown')[:100]}\n"
            prompt += "\n"

        prompt += "Available tools:\n"
        prompt += "\n".join(tool_descriptions)
        prompt += "\n\n"
        prompt += "Rules:\n"
        prompt += "1. Return ONLY one JSON object\n"
        prompt += "2. Use python_exec for multi-step tasks (create file + run)\n"
        prompt += 'Return format: {"tool": "tool_name", "params": {"key": "value"}}'

        self.log(f"LLM prompt:\n{prompt}", "API_REQ")

        try:
            response = self.llm._call(prompt)
            self.log(f"LLM response:\n{response}", "API_RES")
            decision = self._parse_json(response)
            if decision:
                return decision
            raise json.JSONDecodeError("No valid JSON", response, 0)
        except Exception as e:
            self.log(f"Decision failed: {e}", "ERROR")
            return {
                "tool": tool_names[0] if tool_names else "python_exec",
                "params": {"code": f"print('step done: {step_desc}')"}
            }

    def _parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = text[json_start:json_end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
            fixed = json_str.replace('\\n', '\n').replace('\\t', '\t')
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass
            tool_match = re.search(r'"tool"\s*:\s*"([^"]+)"', json_str)
            if tool_match:
                tool_name = tool_match.group(1)
                params = {}
                for key in ["action", "path"]:
                    key_match = re.search(rf'"{key}"\s*:\s*"([^"]+)"', json_str)
                    if key_match:
                        params[key] = key_match.group(1)
                for key in ["content", "code"]:
                    key_match = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', json_str, re.DOTALL)
                    if key_match:
                        val = key_match.group(1)
                        val = val.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
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
