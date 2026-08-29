import json
import time
from typing import Any, Dict, List, Optional
from datetime import datetime
from .llm import LocalLLM
from .tools.base import BaseTool, ToolRegistry
from .memory.base import BaseMemory
from .planner.simple import SimplePlanner


def get_timestamp():
    """"获取时间戳"""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


class Agent:
    """"Agent核心类"""
    
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
        """"记录日志"""
        timestamp = get_timestamp()
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        if self.debug:
            print(log_entry)
        
        self.debug_logs.append({
            "timestamp": timestamp,
            "level": level,
            "message": message
        })
    
    def run(self, goal: str) -> Dict[str, Any]:
        """"运行Agent"""
        self.iteration = 0
        self.debug_logs = []
        step_results = []
        start_time = time.time()
        
        self.log(f"目标: {goal}", "GOAL")
        self.log(f"最大迭代次数: {self.max_iterations}", "CONFIG")
        
        # 创建计划
        plan = self.planner.create_plan(goal)
        plan_id = list(self.planner.plans.keys())[0]
        self.log(f"计划已创建，共{len(plan.steps)}个步骤", "PLAN")
        
        # 记录目标
        if self.memory:
            self.memory.add_message("system", f"目标: {goal}")
        
        while self.iteration < self.max_iterations:
            self.iteration += 1
            iter_start = time.time()
            
            self.log(f"开始第{self.iteration}轮迭代", "ITER")
            
            # 获取下一步
            next_step = self.planner.get_next_step(plan_id)
            if not next_step:
                self.log("没有更多步骤，结束", "PLAN")
                break
            
            self.log(f"当前步骤: {next_step.description}", "STEP")
            
            # 决策：选择工具和参数
            self.log("开始决策...", "DECIDE")
            decision_start = time.time()
            decision = self._make_decision(next_step, goal)
            decision_time = time.time() - decision_start
            
            self.log(f"决策完成 (耗时{decision_time:.2f}秒)", "DECIDE")
            self.log(f"选择工具: {decision.get('tool')}", "TOOL")
            self.log(f"工具参数: {json.dumps(decision.get('params', {}), ensure_ascii=False)}", "TOOL")
            
            # 执行
            self.log("开始执行工具...", "EXEC")
            exec_start = time.time()
            result = self._execute_decision(decision)
            exec_time = time.time() - exec_start
            
            self.log(f"工具执行完成 (耗时{exec_time:.2f}秒)", "EXEC")
            self.log(f"执行结果: {json.dumps(result, ensure_ascii=False)[:200]}", "RESULT")
            
            # 收集结果
            step_results.append({
                "step": next_step.id,
                "description": next_step.description,
                "tool": decision.get("tool"),
                "result": result,
                "decision_time": decision_time,
                "exec_time": exec_time
            })
            
            # 存储结果到记忆
            if self.memory:
                self.memory.add_message("assistant", f"步骤{next_step.id}: {result}")
            
            # 更新计划进度
            if result.get("success", False):
                self.planner.mark_step_completed(plan_id, next_step.id, result)
                self.log(f"步骤{next_step.id}标记为完成", "PLAN")
            else:
                self.planner.mark_step_failed(plan_id, next_step.id, result.get("error"))
                self.log(f"步骤{next_step.id}标记为失败: {result.get('error')}", "PLAN")
            
            iter_time = time.time() - iter_start
            self.log(f"第{self.iteration}轮迭代完成 (耗时{iter_time:.2f}秒)", "ITER")
            
            # 如果这一步成功了，可以提前结束
            if result.get("success"):
                self.log("任务成功完成，提前结束", "DONE")
                break
            
            # 检查是否完成
            if self.planner.is_plan_complete(plan_id):
                self.log("所有步骤已完成", "PLAN")
                break
        
        # 找到最后一个成功的结果
        final_result = None
        for sr in reversed(step_results):
            if sr["result"].get("success"):
                final_result = sr["result"]
                break
        
        total_time = time.time() - start_time
        self.log(f"任务结束，总耗时{total_time:.2f}秒，共{self.iteration}轮迭代", "DONE")
        
        # 返回最终结果
        return {
            "goal": goal,
            "iterations": self.iteration,
            "plan_status": self.planner.get_plan(plan_id).status,
            "final_result": final_result,
            "step_results": step_results,
            "debug_logs": self.debug_logs,
            "total_time": total_time
        }
    
    def _make_decision(self, step, goal: str) -> Dict[str, Any]:
        """"决策：选择工具和参数"""
        # 获取可用工具
        tools = self.tool_registry.list_tools()
        tool_names = [t.name for t in tools]
        
        # 获取工具描述和参数说明
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
        
        # 构建提示词
        prompt = f"目标: {goal}\n当前步骤: {step.description}\n\n"
        prompt += "可用工具:\n"
        prompt += "\n".join(tool_descriptions)
        prompt += "\n\n请选择合适的工具并提供参数。只返回JSON格式，不要返回其他内容。\n"
        prompt += '{"tool": "工具名", "params": {"参数名": "参数值"}}'
        
        self.log(f"发送给LLM的提示词:\n{prompt}", "API_REQ")
        
        # 调用LLM
        try:
            response = self.llm._call(prompt)
            self.log(f"LLM返回的响应:\n{response}", "API_RES")
            
            # 尝试解析JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                decision = json.loads(json_str)
                return decision
            else:
                raise json.JSONDecodeError("No JSON found", response, 0)
        except (json.JSONDecodeError, Exception) as e:
            self.log(f"JSON解析失败: {e}，使用默认决策", "ERROR")
            # 如果解析失败，返回默认决策
            return {
                "tool": tool_names[0] if tool_names else None,
                "params": {"action": "execute", "code": f"print('执行步骤: {step.description}')"}
            }
    
    def _execute_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """"执行决策"""
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
        """"获取记忆摘要"""
        if self.memory:
            return self.memory.get_summary()
        return {"error": "未配置记忆系统"}
