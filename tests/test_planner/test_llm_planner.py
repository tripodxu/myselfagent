import pytest
import json
from unittest.mock import MagicMock, patch
from src.llm import LocalLLM
from src.planner.llm_planner import LLMPlanner


class TestLLMPlanner:
    def setup_method(self):
        self.mock_llm = MagicMock(spec=LocalLLM)
        self.planner = LLMPlanner(llm=self.mock_llm, max_steps=5)

    def test_create_plan_calls_llm(self):
        self.mock_llm._call.return_value = json.dumps({"steps": ["read config", "parse JSON", "extract fields"]})
        plan = self.planner.create_plan("analyze config")
        assert plan is not None
        assert plan.goal == "analyze config"
        assert len(plan.steps) == 3
        assert plan.steps[0].description == "read config"
        assert self.mock_llm._call.called

    def test_create_plan_default_steps_on_llm_failure(self):
        self.mock_llm._call.side_effect = Exception("LLM unavailable")
        plan = self.planner.create_plan("test goal")
        assert plan is not None
        assert len(plan.steps) >= 1
        assert plan.steps[0].description == "test goal"

    def test_create_plan_default_steps_on_invalid_json(self):
        self.mock_llm._call.return_value = "not json"
        plan = self.planner.create_plan("test goal")
        assert plan is not None
        assert len(plan.steps) >= 1

    def test_create_plan_limits_steps(self):
        self.mock_llm._call.return_value = json.dumps({"steps": ["s1","s2","s3","s4","s5","s6","s7"]})
        planner = LLMPlanner(llm=self.mock_llm, max_steps=3)
        plan = planner.create_plan("test goal")
        assert len(plan.steps) <= 3

    def test_create_plan_returns_active_status(self):
        self.mock_llm._call.return_value = json.dumps({"steps": ["step1"]})
        plan = self.planner.create_plan("test goal")
        assert plan.status == "active"

    def test_get_next_step_returns_first_pending(self):
        self.mock_llm._call.return_value = json.dumps({"steps": ["stepA", "stepB", "stepC"]})
        plan = self.planner.create_plan("test goal")
        plan_id = list(self.planner.plans.keys())[0]
        step = self.planner.get_next_step(plan_id)
        assert step.description == "stepA"

    def test_get_next_step_after_completion(self):
        self.mock_llm._call.return_value = json.dumps({"steps": ["stepA", "stepB", "stepC"]})
        plan = self.planner.create_plan("test goal")
        plan_id = list(self.planner.plans.keys())[0]
        self.planner.mark_step_completed(plan_id, 1)
        step = self.planner.get_next_step(plan_id)
        assert step.description == "stepB"

    def test_get_next_step_all_done(self):
        self.mock_llm._call.return_value = json.dumps({"steps": ["stepA"]})
        plan = self.planner.create_plan("test goal")
        plan_id = list(self.planner.plans.keys())[0]
        self.planner.mark_step_completed(plan_id, 1)
        step = self.planner.get_next_step(plan_id)
        assert step is None

    def test_evaluate_result_calls_llm(self):
        self.mock_llm._call.return_value = json.dumps({"action": "continue", "reason": "step done"})
        plan = self.planner.create_plan("test goal")
        plan_id = list(self.planner.plans.keys())[0]
        result = self.planner.evaluate_result(plan_id, step_id=1, result={"success": True, "output": "ok"}, goal="test goal")
        assert result["action"] == "continue"
        assert "reason" in result

    def test_evaluate_result_returns_stop(self):
        self.mock_llm._call.return_value = json.dumps({"action": "stop", "reason": "goal achieved"})
        plan = self.planner.create_plan("calc 6*7")
        plan_id = list(self.planner.plans.keys())[0]
        result = self.planner.evaluate_result(plan_id, step_id=1, result={"success": True, "output": "42"}, goal="calc 6*7")
        assert result["action"] == "stop"

    def test_evaluate_result_returns_replan(self):
        self.mock_llm._call.return_value = json.dumps({"action": "replan", "reason": "file not found", "new_steps": ["search", "create"]})
        plan = self.planner.create_plan("read config")
        plan_id = list(self.planner.plans.keys())[0]
        result = self.planner.evaluate_result(plan_id, step_id=1, result={"success": False, "error": "not found"}, goal="read config")
        assert result["action"] == "replan"
        assert "new_steps" in result

    def test_evaluate_result_on_llm_failure_defaults_to_continue(self):
        self.mock_llm._call.side_effect = Exception("timeout")
        plan = self.planner.create_plan("test goal")
        plan_id = list(self.planner.plans.keys())[0]
        result = self.planner.evaluate_result(plan_id, step_id=1, result={"success": True, "output": "ok"}, goal="test goal")
        assert result["action"] == "continue"

    def test_replan_creates_new_steps(self):
        self.mock_llm._call.return_value = json.dumps({"steps": ["stepA", "stepB", "stepC"]})
        plan = self.planner.create_plan("test goal")
        plan_id = list(self.planner.plans.keys())[0]
        self.planner.mark_step_completed(plan_id, 1)
        self.planner.replan(plan_id, ["newX", "newY"])
        plan = self.planner.get_plan(plan_id)
        assert plan.steps[0].status == "completed"
        remaining = [s for s in plan.steps if s.status == "pending"]
        assert len(remaining) == 2
        assert remaining[0].description == "newX"

    def test_replan_preserves_completed_steps(self):
        self.mock_llm._call.return_value = json.dumps({"steps": ["A", "B", "C"]})
        plan = self.planner.create_plan("test goal")
        plan_id = list(self.planner.plans.keys())[0]
        self.planner.mark_step_completed(plan_id, 1)
        self.planner.replan(plan_id, ["X"])
        plan = self.planner.get_plan(plan_id)
        assert plan.steps[0].description == "A"
        assert plan.steps[0].status == "completed"
        assert plan.steps[1].description == "X"
        assert plan.steps[1].status == "pending"

    def test_get_plan_progress(self):
        self.mock_llm._call.return_value = json.dumps({"steps": ["A", "B", "C"]})
        plan = self.planner.create_plan("test goal")
        plan_id = list(self.planner.plans.keys())[0]
        progress = self.planner.get_plan_progress(plan_id)
        assert progress["total_steps"] == 3
        assert progress["completed"] == 0
        assert progress["status"] == "active"
        self.planner.mark_step_completed(plan_id, 1)
        progress = self.planner.get_plan_progress(plan_id)
        assert progress["completed"] == 1
