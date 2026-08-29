import pytest
from src.planner.simple import SimplePlanner, Plan, Step


class TestSimplePlanner:
    def setup_method(self):
        self.planner = SimplePlanner(max_steps=5)
    
    def test_create_plan(self):
        """"测试创建计划"""
        plan = self.planner.create_plan("写一个计算器程序")
        
        assert plan is not None
        assert plan.goal == "写一个计算器程序"
        assert plan.status == "active"
        assert len(plan.steps) > 0
    
    def test_plan_has_steps(self):
        """"测试计划包含步骤"""
        plan = self.planner.create_plan("测试目标")
        
        assert len(plan.steps) > 0
        assert all(isinstance(s, Step) for s in plan.steps)
        assert all(s.status == "pending" for s in plan.steps)
    
    def test_get_next_step(self):
        """"测试获取下一步"""
        plan = self.planner.create_plan("测试目标")
        
        next_step = self.planner.get_next_step(plan.plan_id if hasattr(plan, 'plan_id') else list(self.planner.plans.keys())[0])
        
        assert next_step is not None
        assert next_step.status == "pending"
        assert next_step.id == 1
    
    def test_update_progress(self):
        """"测试更新进度"""
        plan = self.planner.create_plan("测试目标")
        plan_id = list(self.planner.plans.keys())[0]
        
        # 标记第一步完成
        result = self.planner.mark_step_completed(plan_id, 1, "完成")
        assert result is True
        
        # 验证状态更新
        updated_plan = self.planner.get_plan(plan_id)
        assert updated_plan.steps[0].status == "completed"
        assert updated_plan.steps[0].result == "完成"
    
    def test_plan_completion(self):
        """"测试计划完成状态"""
        plan = self.planner.create_plan("测试目标")
        plan_id = list(self.planner.plans.keys())[0]
        
        # 标记所有步骤完成
        for step in plan.steps:
            self.planner.mark_step_completed(plan_id, step.id)
        
        assert self.planner.is_plan_complete(plan_id) is True
        assert self.planner.get_plan(plan_id).status == "completed"
    
    def test_plan_failure(self):
        """"测试计划失败状态"""
        plan = self.planner.create_plan("测试目标")
        plan_id = list(self.planner.plans.keys())[0]
        
        # 标记一个步骤失败
        self.planner.mark_step_failed(plan_id, 1, "出错了")
        
        plan = self.planner.get_plan(plan_id)
        assert plan.status == "failed"
    
    def test_get_plan_progress(self):
        """"测试获取计划进度"""
        plan = self.planner.create_plan("测试目标")
        plan_id = list(self.planner.plans.keys())[0]
        
        # 完成一半步骤
        self.planner.mark_step_completed(plan_id, 1)
        
        progress = self.planner.get_plan_progress(plan_id)
        
        assert progress["total_steps"] == len(plan.steps)
        assert progress["completed"] == 1
        assert progress["remaining"] == len(plan.steps) - 1
        assert progress["progress"] > 0
    
    def test_get_nonexistent_plan(self):
        """"测试获取不存在的计划"""
        result = self.planner.get_plan("nonexistent")
        assert result is None
    
    def test_max_steps_limit(self):
        """"测试最大步骤数限制"""
        planner = SimplePlanner(max_steps=3)
        plan = planner.create_plan("测试目标")
        
        assert len(plan.steps) <= 3
