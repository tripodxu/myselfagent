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
            "status": plan.status
        }

    def _decompose_with_llm(self, goal: str) -> List[str]:
        if not self.llm:
            return [goal]
        prompt = (
            "Decompose task into atomic executable steps.\n\n"
            "For complex HTML/CSS/JS tasks, break into phases:\n"
            "Phase 1: Read requirements and plan structure\n"
            "Phase 2: Generate base HTML with navigation and hero\n"
            "Phase 3: Add content sections (about, skills, projects)\n"
            "Phase 4: Add interactive features (forms, modals, animations)\n"
            "Phase 5: Add final polish (dark mode, responsive, footer)\n\n"
            "Principles: specific, executable (one tool call per step), logical order.\n\n"
            "Complexity: simple->1 step, medium->2-3 steps, complex->group into phases.\n\n"
            "Output JSON only:\n"
            '{"complexity":"simple|medium|complex","steps":["step1","step2"]}\n\n'
            "Token Budget: output <= 500 tokens. Steps concise.\n\n"
            f"Goal: {goal}\n\n"
            "Rules: max 5 steps, prefer 2-3. No review steps. JSON only."
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
            "Evaluate step result and decide next action.\n\n"
            "## Dimensions (by priority)\n"
            "1. Correctness: result achieves step goal?\n"
            "2. Completeness: all required info present?\n"
            "3. Implementation: real code/data, not plan text/placeholders?\n\n"
            "## Decision Matrix\n"
            "| Status | Action |\n"
            "|--------|--------|\n"
            "| Correct+Complete+Real | continue |\n"
            "| Correct but incomplete | continue |\n"
            "| Plan text/output | replan |\n"
            "| Execution error | continue (adjust) |\n"
            "| Off-target | replan |\n"
            "| All steps done | stop |\n\n"
            "## Verification Step\n"
            "- After generating HTML, verify it contains all required features\n"
            "- Check for: navigation, hero, typing effect, particles, about, skills, projects, contact, footer, dark mode, back to top\n"
            "- If features are missing, replan to add them\n\n"
            "## Key Rules\n"
            "- File read success (file_io returns content) -> continue\n"
            "- Goal from doc: check ALL modules/functions included, missing any = not complete\n"
            "- Output with non-JSON (explanation, code blocks, markdown) -> replan\n"
            "- Placeholder text (Content for XXX, TODO, 待填充) -> replan\n"
            "- Real runnable code/data -> evaluate if meets goal\n\n"
            "## Progress\n"
            f"Goal: {goal}\n"
            f"Completed: {step_desc}\n"
            f"Result: {result_summary}\n"
            f"Remaining: {remaining_text}\n\n"
            "## Token Budget\n"
            "Output <= 500 tokens. Reason concise, 1-2 sentences max.\n\n"
            "Output JSON:\n"
            '{"action":"continue|stop|replan","reason":"why","new_steps":["only for replan"]}\n\n'
            "Examples:\n"
            "Step: created complete HTML with CSS/JS\n"
            '-> {"action":"continue","reason":"step done"}\n\n'
            "Step: output plan text not code\n"
            '-> {"action":"replan","reason":"output is description not implementation","new_steps":["write real HTML code"]}\n\n'
            "Step: all pages created\n"
            '-> {"action":"stop","reason":"goal achieved"}'
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



