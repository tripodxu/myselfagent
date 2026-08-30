import json
import re
from typing import Any, List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Step:
    id: int
    description: str
    status: str = "pending"
    result: Any = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = None


@dataclass
class Plan:
    goal: str
    steps: List[Step] = field(default_factory=list)
    status: str = "active"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = None


class LLMPlanner:
    def __init__(self, llm=None, max_steps: int = 5):
        self.llm = llm
        self.max_steps = max_steps
        self.plans: Dict[str, Plan] = {}

    def create_plan(self, goal: str, plan_id: str = None) -> Plan:
        if plan_id is None:
            plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        steps_desc = self._decompose_with_llm(goal)
        steps = [Step(id=i + 1, description=s) for i, s in enumerate(steps_desc)]
        plan = Plan(goal=goal, steps=steps)
        self.plans[plan_id] = plan
        return plan

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self.plans.get(plan_id)

    def get_next_step(self, plan_id: str) -> Optional[Step]:
        plan = self.get_plan(plan_id)
        if not plan or plan.status != "active":
            return None
        for step in plan.steps:
            if step.status == "pending":
                return step
        return None

    def mark_step_completed(self, plan_id: str, step_id: int, result: Any = None) -> bool:
        plan = self.get_plan(plan_id)
        if not plan:
            return False
        for step in plan.steps:
            if step.id == step_id:
                step.status = "completed"
                step.result = result
                step.completed_at = datetime.now().isoformat()
                self._check_plan_completion(plan_id)
                return True
        return False

    def mark_step_failed(self, plan_id: str, step_id: int, error: str = None) -> bool:
        plan = self.get_plan(plan_id)
        if not plan:
            return False
        for step in plan.steps:
            if step.id == step_id:
                step.status = "failed"
                step.result = error
                self._check_plan_completion(plan_id)
                return True
        return False

    def mark_plan_completed(self, plan_id: str) -> bool:
        plan = self.get_plan(plan_id)
        if not plan:
            return False
        plan.status = "completed"
        plan.completed_at = datetime.now().isoformat()
        return True

    def is_plan_complete(self, plan_id: str) -> bool:
        plan = self.get_plan(plan_id)
        if not plan:
            return False
        return plan.status == "completed"

    def evaluate_result(self, plan_id: str, step_id: int, result: dict, goal: str) -> dict:
        plan = self.get_plan(plan_id)
        if not plan:
            return {"action": "continue", "reason": "plan not found"}
        step_desc = ""
        for s in plan.steps:
            if s.id == step_id:
                step_desc = s.description
                break
        remaining = [s.description for s in plan.steps if s.status == "pending"]
        prompt = self._build_evaluate_prompt(goal, step_desc, result, remaining)
        try:
            response = self.llm._call(prompt)
            parsed = self._parse_json(response)
            if parsed and "action" in parsed:
                return parsed
        except Exception:
            pass
        # Fallback: if no remaining steps, stop; otherwise continue
        if not remaining:
            return {"action": "stop", "reason": "all steps completed"}
        return {"action": "continue", "reason": "evaluation failed, defaulting to continue"}

    def replan(self, plan_id: str, new_steps: List[str]) -> bool:
        plan = self.get_plan(plan_id)
        if not plan:
            return False
        completed = [s for s in plan.steps if s.status == "completed"]
        next_id = len(completed) + 1
        new_step_objects = [Step(id=next_id + i, description=desc, status="pending") for i, desc in enumerate(new_steps)]
        plan.steps = completed + new_step_objects
        plan.status = "active"
        return True

    def get_plan_progress(self, plan_id: str) -> Dict[str, Any]:
        plan = self.get_plan(plan_id)
        if not plan:
            return {"error": "plan not found"}
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

    def _decompose_with_llm(self, goal: str) -> List[str]:
        if not self.llm:
            return [goal]
        prompt = (
            f"Decompose this goal into concrete, actionable steps.\n"
            f"Goal: {goal}\n\n"
            f"Return ONLY a JSON object: {{\"steps\": [\"step1\", \"step2\", ...]}}\n"
            f"Rules:\n"
            f"- Maximum 5 steps, prefer 2-3 steps\n"
            f"- Each step should combine related actions into ONE unit\n"
            f"- Each step should be executable in a single tool call\n"
            f"- Do NOT include review/confirm/evaluate steps\n"
            f"- Steps should be ordered logically\n"
            f"- Do NOT include any text outside the JSON"
        )
        try:
            response = self.llm._call(prompt)
            parsed = self._parse_json(response)
            if parsed and "steps" in parsed and isinstance(parsed["steps"], list):
                steps = [str(s) for s in parsed["steps"] if s]
                return steps[:self.max_steps] if steps else [goal]
        except Exception:
            pass
        return [goal]

    def _build_evaluate_prompt(self, goal: str, step_desc: str, result: dict, remaining: List[str]) -> str:
        result_summary = ""
        if result.get("success"):
            output = result.get("output", "").strip()[:200] or result.get("message", "")[:200]
            result_summary = f"Success: {output}"
        else:
            result_summary = f"Failed: {result.get('error', 'unknown error')[:200]}"
        remaining_text = ", ".join(remaining[:5]) if remaining else "none"
        return (
            f"Goal: {goal}\n"
            f"Completed step: {step_desc}\n"
            f"Step result: {result_summary}\n"
            f"Remaining steps: {remaining_text}\n\n"
            f"CRITICAL EVALUATION - read the output carefully:\n"
            f"- If output contains plan text, markdown, descriptions, or '---' separators: REPLAN with new_steps\n"
            f"- If output is actual working code (HTML tags, Python functions, etc.): evaluate normally\n"
            f"- If output is a placeholder or summary: CONTINUE or REPLAN\n"
            f"- Only say STOP if the goal is truly achieved with COMPLETE, WORKING output\n\n"
            f"Return ONLY a JSON object:\n"
            f'- {{"action": "continue", "reason": "why continue"}} - if goal not yet fully achieved\n'
            f'- {{"action": "stop", "reason": "why stop"}} - if goal is FULLY achieved with correct output\n'
            f'- {{"action": "replan", "reason": "why replan", "new_steps": ["step1", "step2"]}} - if plan needs adjustment'
        )

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
        return None

    def _check_plan_completion(self, plan_id: str) -> None:
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
