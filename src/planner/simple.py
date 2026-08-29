from typing import Any, List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Step:
    """计划步骤"""
    id: int
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Any = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = None


@dataclass
class Plan:
    """计划"""
    goal: str
    steps: List[Step] = field(default_factory=list)
    current_step_index: int = 0
    status: str = "active"  # active, completed, failed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = None


class SimplePlanner:
    """简单规划器"""

    def __init__(self, max_steps: int = 10):
        self.max_steps = max_steps
        self.plans: Dict[str, Plan] = {}

    def create_plan(self, goal: str, plan_id: str = None) -> Plan:
        """创建计划"""
        if plan_id is None:
            plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 分解目标为步骤
        steps = self._decompose_goal(goal)

        plan = Plan(
            goal=goal,
            steps=[Step(id=i+1, description=s) for i, s in enumerate(steps)]
        )

        self.plans[plan_id] = plan
        return plan

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """获取计划"""
        return self.plans.get(plan_id)

    def get_next_step(self, plan_id: str) -> Optional[Step]:
        """获取下一步"""
        plan = self.get_plan(plan_id)
        if not plan or plan.status != "active":
            return None

        for step in plan.steps:
            if step.status == "pending":
                return step

        return None

    def update_step(self, plan_id: str, step_id: int, status: str, result: Any = None) -> bool:
        """更新步骤状态"""
        plan = self.get_plan(plan_id)
        if not plan:
            return False

        for step in plan.steps:
            if step.id == step_id:
                step.status = status
                step.result = result
                if status == "completed":
                    step.completed_at = datetime.now().isoformat()

                # 检查是否所有步骤都完成
                self._check_plan_completion(plan_id)
                return True

        return False

    def mark_step_completed(self, plan_id: str, step_id: int, result: Any = None) -> bool:
        """标记步骤完成"""
        return self.update_step(plan_id, step_id, "completed", result)

    def mark_step_failed(self, plan_id: str, step_id: int, error: str = None) -> bool:
        """标记步骤失败"""
        return self.update_step(plan_id, step_id, "failed", error)

    def mark_plan_completed(self, plan_id: str) -> bool:
        """手动标记计划完成（由Agent在任务结束时调用）"""
        plan = self.get_plan(plan_id)
        if not plan:
            return False
        plan.status = "completed"
        plan.completed_at = datetime.now().isoformat()
        return True

    def is_plan_complete(self, plan_id: str) -> bool:
        """检查计划是否完成"""
        plan = self.get_plan(plan_id)
        if not plan:
            return False
        return plan.status == "completed"

    def get_plan_progress(self, plan_id: str) -> Dict[str, Any]:
        """获取计划进度"""
        plan = self.get_plan(plan_id)
        if not plan:
            return {"error": "计划不存在"}

        completed = sum(1 for s in plan.steps if s.status == "completed")
        total = len(plan.steps)

        return {
            "goal": plan.goal,
            "total_steps": total,
            "completed": completed,
            "remaining": total - completed,
            "progress": completed / total if total > 0 else 0,
            "status": plan.status,
            "current_step": self.get_next_step(plan_id)
        }

    def _decompose_goal(self, goal: str) -> List[str]:
        """分解目标为步骤"""
        # 初始版本：将整个目标作为单个步骤
        # Agent循环会通过LLM自主决定如何完成
        return [goal]

    def _check_plan_completion(self, plan_id: str) -> None:
        """检查计划是否完成"""
        plan = self.get_plan(plan_id)
        if not plan:
            return

        all_completed = all(s.status == "completed" for s in plan.steps)
        any_failed = any(s.status == "failed" for s in plan.steps)

        if all_completed:
            plan.status = "completed"
            plan.completed_at = datetime.now().isoformat()
        elif any_failed:
            plan.status = "failed"
