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
            
            # 存储结果到记忆
            if self.memory:
                self.memory.add_message("assistant", f"步骤{next_step.id}: {result}")
            
            # 更新计划进度
            if result.get("success", False):
                self.planner.mark_step_completed(plan_id, next_step.id, result)
            else:
                self.planner.mark_step_failed(plan_id, next_step.id, result.get("error"))
            
            # 检查是否完成
            if self.planner.is_plan_complete(plan_id):
                break
        
        # 返回最终结果
        return {
            "goal": goal,
            "iterations": self.iteration,
            "plan_status": self.planner.get_plan(plan_id).status,
            "progress": self.planner.get_plan_progress(plan_id)
        }
    
    def _make_decision(self, step, goal: str) -> Dict[str, Any]:
        """"决策：选择工具和参数"""
        # 获取可用工具
        tools = self.tool_registry.list_tools()
        tool_names = [t.name for t in tools]
        
        # 构建提示词
        prompt = f"""
目标: {goal}
当前步骤: {step.description}
可用工具: {tool_names}

请选择合适的工具并提供参数。返回JSON格式:
{{"tool": "工具名", "params": {{"参数名": "参数值"}}}}
"""
        
        # 调用LLM
        try:
            response = self.llm._call(prompt)
            # 尝试解析JSON
            decision = json.loads(response)
            return decision
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
