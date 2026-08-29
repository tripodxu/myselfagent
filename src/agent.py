import json
import re
import sys
import time
from typing import Any, Dict, List, Optional
from datetime import datetime
from .llm import LocalLLM
from .tools.base import BaseTool, ToolRegistry
from .memory.base import BaseMemory
from .planner.simple import SimplePlanner


def get_timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def has_answer(result: dict) -> bool:
    """检查结果是否包含实际答案（不只是success状态）"""
    if not result.get("success"):
        return False

    # 检查是否有实际输出内容
    output = result.get("output", "")
    if output and len(str(output).strip()) > 0:
        # 排除无意义的fallback输出
        stripped = str(output).strip()
        fallback_markers = ["执行步骤:", "执行步骤：", "步骤完成:", "步骤完成："]
        if any(marker in stripped for marker in fallback_markers):
            return False
        return True

    # 检查是否有日期/时间结果
    if result.get("date") or result.get("time") or result.get("weekday") or result.get("datetime"):
        return True

    # 检查是否有文件内容
    if result.get("content"):
        return True

    # 检查是否有具体结果
    if result.get("result"):
        return True

    return False


def select_best_result(step_results: list) -> dict:
    """从所有步骤结果中选择最佳答案"""
    successful = [r for r in step_results if r.get("result", {}).get("success")]
    if not successful:
        return {}

    # 优先选择包含实际答案的结果
    with_answer = [r for r in successful if has_answer(r["result"])]
    if with_answer:
        # 优先选择有output的结果（通常是代码执行的实际输出）
        with_output = [r for r in with_answer if r["result"].get("output")]
        if with_output:
            return with_output[-1]["result"]
        return with_answer[-1]["result"]

    # 退而求其次，返回最后一个成功结果
    return successful[-1]["result"]


class Agent:
    def __init__(
        self,
        llm: LocalLLM = None,
        memory: BaseMemory = None,
        planner: SimplePlanner = None,
        tool_registry: ToolRegistry = None,
        max_iterations: int = 10,
        debug: bool = False
    ):
        self.llm = llm or LocalLLM()
        self.memory = memory
        self.planner = planner or SimplePlanner()
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
            except UnicodeEncodeError:
                print(log_entry.encode('utf-8', errors='replace').decode('utf-8'), flush=True)
            except ValueError:
                pass
        self.debug_logs.append({"timestamp": timestamp, "level": level, "message": message})

    def run(self, goal: str) -> Dict[str, Any]:
        self.iteration = 0
        self.debug_logs = []
        step_results = []
        start_time = time.time()

        self.log(f"目标: {goal}", "GOAL")
        self.log(f"最大迭代次数: {self.max_iterations}", "CONFIG")

        # 创建计划（仅用于进度跟踪，不强制步骤）
        plan = self.planner.create_plan(goal)
        plan_id = list(self.planner.plans.keys())[0]
        self.log(f"计划已创建，共{len(plan.steps)}个步骤", "PLAN")

        if self.memory:
            self.memory.add_message("system", f"目标: {goal}")

        while self.iteration < self.max_iterations:
            self.iteration += 1
            iter_start = time.time()

            self.log(f"开始第{self.iteration}轮迭代", "ITER")

            # 获取下一步（仅用于描述，不影响循环）
            next_step = self.planner.get_next_step(plan_id)
            step_desc = next_step.description if next_step else goal
            self.log(f"当前步骤: {step_desc}", "STEP")

            # 决策 - 传入之前的结果作为上下文
            self.log("开始决策...", "DECIDE")
            decision_start = time.time()
            decision = self._make_decision(step_desc, goal, step_results)
            decision_time = time.time() - decision_start

            self.log(f"决策完成 (耗时{decision_time:.2f}秒)", "DECIDE")
            self.log(f"选择工具: {decision.get('tool')}", "TOOL")

            params_str = json.dumps(decision.get('params', {}), ensure_ascii=False)[:200]
            self.log(f"工具参数: {params_str}", "TOOL")

            # 执行
            self.log("开始执行工具...", "EXEC")
            exec_start = time.time()
            result = self._execute_decision(decision)
            exec_time = time.time() - exec_start

            self.log(f"工具执行完成 (耗时{exec_time:.2f}秒)", "EXEC")

            try:
                result_str = json.dumps(result, ensure_ascii=False)[:300]
            except (TypeError, ValueError):
                result_str = str(result)[:300]
            self.log(f"执行结果: {result_str}", "RESULT")

            step_results.append({
                "step": self.iteration,
                "description": step_desc,
                "tool": decision.get("tool"),
                "result": result,
                "decision_time": decision_time,
                "exec_time": exec_time
            })

            if self.memory:
                self.memory.add_message("assistant", f"步骤{self.iteration}: {result_str}")

            # 标记planner步骤完成（仅用于进度跟踪）
            if next_step and result.get("success", False):
                self.planner.mark_step_completed(plan_id, next_step.id, result)
                self.log(f"步骤{next_step.id}标记为完成", "PLAN")

            iter_time = time.time() - iter_start
            self.log(f"第{self.iteration}轮迭代完成 (耗时{iter_time:.2f}秒)", "ITER")

            # 关键修复：检查是否已获得答案
            if has_answer(result):
                self.log("检测到实际答案，提前结束", "DONE")
                break

            # 检查planner是否全部完成
            if self.planner.is_plan_complete(plan_id):
                self.log("所有计划步骤已完成", "PLAN")
                break

        # 选择最佳结果
        final_result = select_best_result(step_results)

        total_time = time.time() - start_time
        self.log(f"任务结束，总耗时{total_time:.2f}秒，共{self.iteration}轮迭代", "DONE")

        self.planner.mark_plan_completed(plan_id)

        return {
            "goal": goal,
            "iterations": self.iteration,
            "plan_status": "completed",
            "final_result": final_result,
            "step_results": step_results,
            "total_time": total_time
        }

    def _make_decision(self, step_desc: str, goal: str, prior_results: list = None) -> Dict[str, Any]:
        tools = self.tool_registry.list_tools()
        tool_names = [t.name for t in tools]

        tool_descriptions = []
        for tool in tools:
            desc = f"- {tool.name}: {tool.description}"
            if tool.name == "datetime":
                desc += "\n  参数: action (可选: now, date, time, weekday, 后天, 大后天, 昨天, 前天, +N, -N)"
            elif tool.name == "python_exec":
                desc += "\n  参数: code (Python代码字符串)"
            elif tool.name == "file_io":
                desc += "\n  参数: action (read/write/list), path, content"
            elif tool.name == "search":
                desc += "\n  参数: action (text/file/files), pattern, text/target"
            tool_descriptions.append(desc)

        prompt = f"目标: {goal}\n\n"

        # 关键修复：传入之前的执行结果
        if prior_results:
            prompt += "已完成的步骤和结果:\n"
            for pr in prior_results[-3:]:
                r = pr["result"]
                if r.get("success"):
                    summary = r.get("output", "").strip()[:200] or r.get("message", "")[:200] or json.dumps(r, ensure_ascii=False)[:200]
                    prompt += f"- 步骤{pr['step']}: 使用{pr['tool']} -> {summary}\n"
                else:
                    prompt += f"- 步骤{pr['step']}: 使用{pr['tool']} -> 失败: {r.get('error', '未知错误')[:100]}\n"
            prompt += "\n"

        prompt += "可用工具:\n"
        prompt += "\n".join(tool_descriptions)
        prompt += "\n\n"
        prompt += "重要规则：\n"
        prompt += "1. 只返回一个JSON，不要返回其他任何内容\n"
        prompt += "2. 用python_exec工具可以一次完成多步操作（创建文件+运行）\n"
        prompt += "3. 如果之前的步骤已经完成了目标，不需要再调用工具\n"
        prompt += '\n返回格式: {"tool": "工具名", "params": {"参数名": "参数值"}}'

        self.log(f"发送给LLM的提示词:\n{prompt}", "API_REQ")

        try:
            response = self.llm._call(prompt)
            self.log(f"LLM返回的响应:\n{response}", "API_RES")

            decision = self._parse_json(response)
            if decision:
                return decision
            else:
                raise json.JSONDecodeError("No valid JSON found", response, 0)
        except (json.JSONDecodeError, Exception) as e:
            self.log(f"决策失败: {e}，使用默认决策", "ERROR")
            return {
                "tool": tool_names[0] if tool_names else "python_exec",
                "params": {"code": f"print('步骤完成: {step_desc}')"}
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

                action_match = re.search(r'"action"\s*:\s*"([^"]+)"', json_str)
                if action_match:
                    params["action"] = action_match.group(1)

                path_match = re.search(r'"path"\s*:\s*"([^"]+)"', json_str)
                if path_match:
                    params["path"] = path_match.group(1)

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
            return {"success": False, "error": "未指定工具"}

        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            return {"success": False, "error": f"工具不存在: {tool_name}"}

        try:
            result = tool.execute(**params)
            return result if isinstance(result, dict) else {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_memory_summary(self) -> Dict[str, Any]:
        if self.memory:
            return self.memory.get_summary()
        return {"error": "未配置记忆系统"}
