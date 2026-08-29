import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from .llm import LocalLLM
from .tools.base import BaseTool, ToolRegistry
from .memory.base import BaseMemory
from .planner.simple import SimplePlanner


class Agent:
    """"Agent核心类"""
    
    def __init__(
        self,
        llm: LocalLLM = None,
        memory: BaseMemory = None,
        planner: SimplePlanner = None,
        tool_registry: ToolRegistry = None,
        max_iterations: int = 10
    ):
        self.llm = llm or LocalLLM()
        self.memory = memory
        self.planner = planner or SimplePlanner()
        self.tool_registry = tool_registry or ToolRegistry()
        self.max_iterations = max_iterations
        self.iteration = 0
    
    def run(self, goal: str) -> Dict[str, Any]:
        """"运行Agent"""
        self.iteration = 0
        step_results = []  # 收集所有步骤结果
        
        # 创建计划
        plan = self.planner.create_plan(goal)
        plan_id = list(self.planner.plans.keys())[0]
        
        # 记录目标
        if self.memory:
            self.memory.add_message("system", f"目标: {goal}")
        
        while self.iteration < self.max_iterations:
            self.iteration += 1
            
            # 获取下一步
            next_step = self.planner.get_next_step(plan_id)
            if not next_step:
                break
            
            # 决策：选择工具和参数
            decision = self._make_decision(next_step, goal)
            
            # 执行
            result = self._execute_decision(decision)
            
            # 收集结果
            step_results.append({
                "step": next_step.id,
                "description": next_step.description,
                "tool": decision.get("tool"),
                "result": result
            })
            
            # 存储结果到记忆
            if self.memory:
                self.memory.add_message("assistant", f"步骤{next_step.id}: {result}")
            
            # 更新计划进度
            if result.get("success", False):
                self.planner.mark_step_completed(plan_id, next_step.id, result)
            else:
                self.planner.mark_step_failed(plan_id, next_step.id, result.get("error"))
            
            # 如果这一步成功了，可以提前结束
            if result.get("success"):
                break
            
            # 检查是否完成
            if self.planner.is_plan_complete(plan_id):
                break
        
        # 找到最后一个成功的结果
        final_result = None
        for sr in reversed(step_results):
            if sr["result"].get("success"):
                final_result = sr["result"]
                break
        
        # 返回最终结果
        return {
            "goal": goal,
            "iterations": self.iteration,
            "plan_status": self.planner.get_plan(plan_id).status,
            "final_result": final_result,
            "step_results": step_results
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
                desc += "\n  参数: action (可选: now, date, time, weekday)"
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
        
        # 调用LLM
        try:
            response = self.llm._call(prompt)
            # 尝试解析JSON
            # 提取JSON部分（可能包含其他文本）
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                decision = json.loads(json_str)
                return decision
            else:
                raise json.JSONDecodeError("No JSON found", response, 0)
        except (json.JSONDecodeError, Exception) as e:
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
