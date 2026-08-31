import json
import re
import time
from typing import Any, Dict, List, Optional
from datetime import datetime
from .llm import LocalLLM
from .tools.base import BaseTool, ToolRegistry
from .memory.base import BaseMemory
from .memory.context_manager import ContextManager
from .planner.llm_planner import LLMPlanner


def get_timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


DANGEROUS_PATTERNS = [
    "rm -rf", "rmdir /s", "del /f",
    "format c:", "shutdown",
    "import subprocess", "import shutil", "import socket",
    "os.system(", "os.popen(",
]


def has_answer(result: dict) -> bool:
    """Check if a result contains a meaningful answer.
    NOTE: This is ONLY used for selecting best result, NOT for early termination.
    """
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
        self.context = ContextManager(memory=memory, max_tokens=3000)
        self.planner = planner or LLMPlanner(llm=self.llm)
        self.tool_registry = tool_registry or ToolRegistry()
        self.max_iterations = max_iterations
        self.iteration = 0
        self.debug = debug
        self.debug_logs = []

    def log(self, message: str, level: str = "INFO"):
        timestamp = get_timestamp()
        log_entry = "[" + timestamp + "] [" + level + "] " + message
        if self.debug:
            try:
                print(log_entry, flush=True)
            except (UnicodeEncodeError, ValueError):
                pass
        self.debug_logs.append({"timestamp": timestamp, "level": level, "message": message})

    def export_logs(self, filepath: str = None) -> str:
        """Export complete debug logs to a txt file."""
        import os
        from datetime import datetime

        if filepath is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
            os.makedirs(log_dir, exist_ok=True)
            filepath = os.path.join(log_dir, f"agent_log_{ts}.txt")

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\\n")
            f.write("MySelfAgent - Complete Execution Log\\n")
            f.write("=" * 60 + "\\n\\n")

            for entry in self.debug_logs:
                line = "[" + entry["timestamp"] + "] [" + entry["level"] + "] " + entry["message"]
                f.write(line + "\\n")

            f.write("\\n" + "=" * 60 + "\\n")
            f.write(f"Total entries: {len(self.debug_logs)}\\n")
            f.write("=" * 60 + "\\n")

        return filepath

    def _check_safety(self, decision: dict) -> dict:
        """Review tool call for safety before execution."""
        tool_name = decision.get("tool", "")
        params = decision.get("params", {})
        for key, val in params.items():
            if isinstance(val, str):
                for pattern in DANGEROUS_PATTERNS:
                    if pattern.lower() in val.lower():
                        self.log("Safety block: " + pattern + " in " + key, "SAFETY")
                        return {"safe": False, "reason": "Blocked: contains '" + pattern + "'"}
        if not self.tool_registry.has_tool(tool_name):
            return {"safe": False, "reason": "Unknown tool: " + tool_name}
        return {"safe": True, "reason": "ok"}

    def _build_messages(self, goal: str, step_desc: str, prior_results: list) -> list:
        """Build layered messages with context management."""
        messages = []
        tool_defs = self.tool_registry.get_tool_definitions()
        tools_text = json.dumps(tool_defs, ensure_ascii=False, indent=2)
        developer_content = (
            "You are an AI agent that EXECUTES tasks by WRITING REAL CODE.\n"
            "CRITICAL RULES:\n"
            "1. Return ONLY JSON: {\"tool\": \"tool_name\", \"params\": {\"key\": \"value\"}}\n"
            "2. Write COMPLETE, RUNNABLE code - NOT placeholders\n"
            "3. For HTML projects: use python_exec to write the file\n"
            "4. NEVER output plan text or descriptions as file content\n"
            "5. Implement ALL features from requirements, including:\n"
            "   - Typing effect for hero section\n"
            "   - Particle background using Canvas API\n"
            "   - Dashboard stats with counter animation\n"
            "   - 3D flip cards with CSS transform\n"
            "   - Radar chart using Canvas API\n"
            "   - Project filtering with data attributes\n"
            "   - Blog section with cards\n"
            "   - Testimonials carousel with auto-play\n"
            "   - Multi-step form with validation\n"
            "   - File upload with drag & drop\n"
            "   - Dark mode toggle with localStorage\n"
            "   - Back to top button\n"
            "6. Combine ALL operations into ONE python_exec call\n\n"
            "Available tools:\n" + tools_text + "\n\n"
            "Output format:\n"
            "{\"tool\": \"tool_name\", \"params\": {\"key\": \"value\"}}\n\n"
            "Token Budget: Completion tokens minimal. Code exempt. Other output <= 500 tokens."
        )
        messages.append({"role": "developer", "content": developer_content})
        user_content = "Goal: " + goal + "\nCurrent step: " + step_desc
        messages.append({"role": "user", "content": user_content})
        if prior_results:
            history_lines = []
            for pr in prior_results[-3:]:
                r = pr["result"]
                step_num = pr["step"]
                tool_name = pr["tool"]
                if r.get("success"):
                    summary = r.get("output", "").strip()[:200] or r.get("message", "")[:200]
                    history_lines.append("Step " + str(step_num) + ": " + str(tool_name) + " -> " + summary)
                else:
                    err_msg = r.get("error", "unknown")[:100]
                    history_lines.append("Step " + str(step_num) + ": " + str(tool_name) + " -> FAILED: " + err_msg)
            messages.append({"role": "assistant", "content": "Previous results:\n" + "\n".join(history_lines)})
        stats = self.context.get_stats()
        if stats["has_summary"]:
            messages.insert(1, {"role": "system", "content": "Context summary: " + self.context.summary})
        return messages

    def run(self, goal: str) -> Dict[str, Any]:
        self.iteration = 0
        self.debug_logs = []
        step_results = []
        start_time = time.time()
        last_eval_action = "continue"

        self.log("Goal: " + goal, "GOAL")
        max_iter_str = str(self.max_iterations)
        self.log("Max iterations: " + max_iter_str, "CONFIG")

        effort = self._estimate_complexity(goal)
        self.llm.set_reasoning_effort(effort)
        self.log("Reasoning effort: " + effort, "CONFIG")

        # Phase 1: LLM decomposes goal into plan
        self.log("Creating plan with LLM...", "PLAN")
        plan = self.planner.create_plan(goal)
        plan_id = list(self.planner.plans.keys())[-1]
        progress = self.planner.get_plan_progress(plan_id)
        total_steps = progress["total_steps"]
        self.log("Plan created: " + str(total_steps) + " steps", "PLAN")
        for i, s in enumerate(plan.steps):
            self.log("  Step " + str(i + 1) + ": " + s.description, "PLAN")

        if self.memory:
            self.context.add_message("system", "Goal: " + goal)

        # Phase 2: Execute plan with feedback loop
        while self.iteration < self.max_iterations:
            self.iteration += 1
            iter_start = time.time()

            next_step = self.planner.get_next_step(plan_id)
            if not next_step:
                # No more steps but LLM says goal not achieved -> replan
                if last_eval_action == "continue":
                    self.log("No more steps but goal not achieved, requesting replan...", "PLAN")
                    replan_prompt = (
                        "Goal: " + goal + "\n"
                        "All planned steps completed but goal is NOT fully achieved.\n"
                        "What additional steps are needed?\n"
                        "Return ONLY a JSON object: {\"steps\": [\"step1\", \"step2\"]}"
                    )
                    try:
                        replan_response = self.llm._call(replan_prompt)
                        replan_parsed = self.planner._parse_json(replan_response)
                        if replan_parsed and "steps" in replan_parsed:
                            new_steps = replan_parsed["steps"]
                            self.log("Replan: " + str(len(new_steps)) + " new steps", "PLAN")
                            for ns in new_steps:
                                self.log("  + " + ns, "PLAN")
                            self.planner.replan(plan_id, new_steps)
                            last_eval_action = "continue"
                            continue
                    except Exception as e:
                        self.log("Replan failed: " + str(e), "ERROR")
                self.log("No more steps in plan", "PLAN")
                break

            step_id_str = str(next_step.id)
            self.log("Iter " + str(self.iteration) + ": Step " + step_id_str + " - " + next_step.description, "ITER")

            # Decide
            self.log("Deciding...", "DECIDE")
            decision_start = time.time()
            decision = self._make_decision(next_step.description, goal, step_results)
            decision_time = time.time() - decision_start
            self.log("Decision: " + f"{decision_time:.2f}" + "s", "DECIDE")
            tn = decision.get("tool")
            self.log("Tool: " + str(tn), "TOOL")

            # Safety review
            safety = self._check_safety(decision)
            safety_reason = safety["reason"]
            self.log("Safety: " + safety_reason, "SAFETY")
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
            self.log("Executed: " + f"{exec_time:.2f}" + "s", "EXEC")

            # Verify output is actual implementation
            result = self._verify_output(decision, result, goal)

            try:
                result_str = json.dumps(result, ensure_ascii=False)[:300]
            except (TypeError, ValueError):
                result_str = str(result)[:300]
            self.log("Result: " + result_str, "RESULT")

            step_results.append({"step": self.iteration, "description": next_step.description,
                                 "tool": decision.get("tool"), "result": result,
                                 "decision_time": decision_time, "exec_time": exec_time})

            if self.memory:
                self.context.add_message("assistant", "Step " + str(self.iteration) + ": " + result_str)

            if result.get("success", False):
                self.planner.mark_step_completed(plan_id, next_step.id, result)
            else:
                self.planner.mark_step_failed(plan_id, next_step.id, result.get("error"))

            iter_time = time.time() - iter_start
            self.log("Iter " + str(self.iteration) + " done: " + f"{iter_time:.2f}" + "s", "ITER")

            # Evaluate: LLM decides continue/stop/replan
            self.log("Evaluating...", "EVAL")
            evaluation = self.planner.evaluate_result(plan_id, next_step.id, result, goal)
            action = evaluation.get("action", "continue")
            reason = evaluation.get("reason", "")
            last_eval_action = action
            self.log("Eval: " + action + " - " + reason, "EVAL")

            if action == "stop":
                self.log("LLM says stop - goal achieved", "DONE")
                break
            elif action == "replan":
                new_steps = evaluation.get("new_steps", [])
                if new_steps:
                    self.log("Replanning: " + str(len(new_steps)) + " new steps", "PLAN")
                    self.planner.replan(plan_id, new_steps)

        # Phase 3: Final result selection
        final_result = select_best_result(step_results)
        total_time = time.time() - start_time
        ctx_stats = self.context.get_stats()
        est_tok = ctx_stats["estimated_tokens"]
        util = ctx_stats["utilization"] * 100
        self.log("Context: " + str(est_tok) + " tokens, " + f"{util:.0f}" + "% used", "CTX")
        self.log("Done: " + f"{total_time:.2f}" + "s, " + str(self.iteration) + " iters", "DONE")

        self.planner.mark_plan_completed(plan_id)
        progress = self.planner.get_plan_progress(plan_id)

        return {"goal": goal, "iterations": self.iteration, "plan_status": "completed",
                "final_result": final_result, "step_results": step_results,
                "total_time": total_time, "progress": progress}

    def _make_decision(self, step_desc: str, goal: str, prior_results: list = None) -> Dict[str, Any]:
        messages = self._build_messages(goal, step_desc, prior_results or [])
        parts = []
        for m in messages:
            role = m["role"].upper()
            content = m["content"]
            parts.append("[" + role + "]\n" + content)
        prompt = "\n\n".join(parts)
        for m in messages:
            role = m["role"].upper()
            content_preview = m["content"]  # No truncation for full logs
            self.log("[" + role + "] " + content_preview, "MSG")
        self.log("Full prompt sent to LLM", "API_REQ")
        tools = self.tool_registry.list_tools()
        tool_names = [t.name for t in tools]
        try:
            response = self.llm._call(prompt)
            if self.llm.use_stream and self.debug:
                self.log("LLM response complete (" + str(len(response)) + " chars)", "API_RES")
            else:
                self.log("LLM response: " + response, "API_RES")  # No truncation
            decision = self._parse_json(response)
            if decision:
                return decision
            raise json.JSONDecodeError("No valid JSON", response, 0)
        except Exception as e:
            self.log("Decision failed: " + str(e), "ERROR")
            fallback_tool = tool_names[0] if tool_names else "python_exec"
            return {"tool": fallback_tool,
                    "params": {"code": "print('step done: " + step_desc + "')"}}

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
            tool_match = re.search(r'"tool"\s*:\s*"([^"]+)"', json_str)
            if tool_match:
                tool_name = tool_match.group(1)
                params = {}
                for key in ["action", "path"]:
                    pat = '"' + key + r'"\s*:\s*"([^"]+)"'
                    km = re.search(pat, json_str)
                    if km:
                        params[key] = km.group(1)
                for key in ["content", "code"]:
                    pat2 = '"' + key + r'"\s*:\s*"((?:[^"\\]|\\.)*)"'
                    km = re.search(pat2, json_str, re.DOTALL)
                    if km:
                        val = km.group(1).replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\\\", "\\")
                        params[key] = val
                return {"tool": tool_name, "params": params}
        return None

    def _verify_output(self, decision: dict, result: dict, goal: str) -> dict:
        """Verify that tool output is actual implementation, not plan text."""
        if not result.get("success"):
            return result

        tool_name = decision.get("tool", "")
        params = decision.get("params", {})

        # Only verify file_io write operations
        if tool_name != "file_io" or params.get("action") != "write":
            return result

        filepath = params.get("path", "")
        if not filepath:
            return result

        # Read back the file to verify
        read_result = self._execute_decision({"tool": "file_io", "params": {"action": "read", "path": filepath}})
        if not read_result.get("success"):
            return result

        content = read_result.get("content", "")

        # Check if content looks like plan text instead of actual code
        plan_markers = ["---", "## ", "### ", "> 可根据", "> **注意**"]
        plan_count = sum(1 for marker in plan_markers if marker in content)

        if plan_count >= 3 and len(content) > 500:
            self.log("Output verification: file contains plan text, not actual code", "VERIFY")
            return {"success": False, "error": "OUTPUT_IS_PLAN_TEXT: File contains plan/description text instead of actual implementation. Write REAL code.", "content": content}

        self.log("Output verification: OK (" + str(len(content)) + " chars)", "VERIFY")
        return result

    def _execute_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = decision.get("tool")
        params = decision.get("params", {})
        if not tool_name:
            return {"success": False, "error": "no tool specified"}
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            return {"success": False, "error": "tool not found: " + str(tool_name)}
        try:
            result = tool.execute(**params)
            return result if isinstance(result, dict) else {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_memory_summary(self) -> Dict[str, Any]:
        if self.memory:
            return self.memory.get_summary()
        return {"error": "no memory configured"}

