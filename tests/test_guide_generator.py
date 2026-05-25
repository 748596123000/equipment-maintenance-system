"""
作业指引生成器测试

测试GuideGenerator类的各项功能：
- GuideStep和WorkGuide数据结构
- 提示词构建
- 响应解析
- 流式生成
- 合规校验
- 个性化推送
"""

import pytest
from unittest.mock import patch, MagicMock

from app.core.guide_generator import (
    GuideStep,
    WorkGuide,
    GuideGenerator,
)


class TestGuideStep:
    """GuideStep作业步骤测试类"""

    def test_guide_step_creation(self):
        """测试GuideStep创建"""
        step = GuideStep(
            step_number=1,
            title="测试步骤",
            description="这是测试步骤的详细描述",
            warnings=["安全警告1"],
            tools_required=["工具1", "工具2"],
            estimated_time="30分钟",
            tips=["操作提示1"]
        )
        assert step.step_number == 1
        assert step.title == "测试步骤"
        assert step.description == "这是测试步骤的详细描述"
        assert step.warnings == ["安全警告1"]
        assert step.tools_required == ["工具1", "工具2"]
        assert step.estimated_time == "30分钟"
        assert step.tips == ["操作提示1"]

    def test_guide_step_to_dict(self):
        """测试GuideStep转字典"""
        step = GuideStep(
            step_number=1,
            title="测试步骤",
            description="描述",
        )
        result = step.to_dict()
        assert result["step_number"] == 1
        assert result["title"] == "测试步骤"
        assert result["description"] == "描述"
        assert result["warnings"] == []
        assert result["tools_required"] == []
        assert result["estimated_time"] is None
        assert result["tips"] == []

    def test_guide_step_defaults(self):
        """测试GuideStep默认值"""
        step = GuideStep(
            step_number=1,
            title="测试",
            description="描述",
        )
        assert step.warnings == []
        assert step.tools_required == []
        assert step.tips == []


class TestWorkGuide:
    """WorkGuide作业指引测试类"""

    def test_work_guide_creation(self):
        """测试WorkGuide创建"""
        steps = [
            GuideStep(step_number=1, title="步骤1", description="描述1"),
            GuideStep(step_number=2, title="步骤2", description="描述2"),
        ]
        guide = WorkGuide(
            title="测试指引",
            task_summary="任务概述",
            preparation=["准备1", "准备2"],
            steps=steps,
            safety_notes=["安全注意1"],
            completion_criteria=["完成标准1"],
            references=[{"id": "1", "title": "参考1"}],
        )
        assert guide.title == "测试指引"
        assert guide.task_summary == "任务概述"
        assert guide.preparation == ["准备1", "准备2"]
        assert len(guide.steps) == 2
        assert guide.safety_notes == ["安全注意1"]
        assert guide.completion_criteria == ["完成标准1"]
        assert guide.references == [{"id": "1", "title": "参考1"}]

    def test_work_guide_to_dict(self):
        """测试WorkGuide转字典"""
        guide = WorkGuide(
            title="测试指引",
            task_summary="概述",
            preparation=["准备"],
            steps=[GuideStep(step_number=1, title="步骤", description="描述")],
            safety_notes=["安全"],
            completion_criteria=["标准"],
            references=[],
        )
        result = guide.to_dict()
        assert result["title"] == "测试指引"
        assert result["task_summary"] == "概述"
        assert len(result["steps"]) == 1
        assert result["compliance_checks"] == []
        assert result["personalized_tips"] == []


class TestGuideGenerator:
    """GuideGenerator作业指引生成器测试类"""

    @patch("app.core.guide_generator.get_llm_service")
    @patch("app.core.guide_generator.get_retriever")
    def test_guide_generator_init(self, mock_retriever, mock_llm):
        """测试GuideGenerator初始化"""
        generator = GuideGenerator()
        assert generator.llm_service is not None
        assert generator.retriever is not None

    @patch("app.core.guide_generator.get_llm_service")
    @patch("app.core.guide_generator.get_retriever")
    def test_build_guide_prompt(self, mock_retriever, mock_llm):
        """测试提示词构建"""
        generator = GuideGenerator()
        prompt = generator._build_guide_prompt(
            task_description="检修变压器",
            equipment_model="10kV变压器",
            equipment_type="变压器",
            fault_type="绝缘故障",
            safety_level="high",
            detail_level="detailed",
            knowledge_context="相关知识上下文",
        )
        assert "检修变压器" in prompt
        assert "10kV变压器" in prompt
        assert "变压器" in prompt
        assert "绝缘故障" in prompt

    @patch("app.core.guide_generator.get_llm_service")
    @patch("app.core.guide_generator.get_retriever")
    def test_parse_guide_response(self, mock_retriever, mock_llm):
        """测试响应解析"""
        generator = GuideGenerator()
        response = '''{
            "title": "变压器检修作业指引",
            "task_summary": "对10kV变压器进行定期检修",
            "preparation": ["确认设备停电", "准备工具"],
            "steps": [
                {
                    "step_number": 1,
                    "title": "外观检查",
                    "description": "检查变压器外观是否有破损",
                    "warnings": ["注意安全距离"],
                    "tools_required": ["望远镜"],
                    "estimated_time": "10分钟",
                    "tips": ["从上到下检查"]
                }
            ],
            "safety_notes": ["全程佩戴安全帽"],
            "completion_criteria": ["外观检查通过"]
        }'''
        guide = generator._parse_guide_response(response)
        assert guide.title == "变压器检修作业指引"
        assert guide.task_summary == "对10kV变压器进行定期检修"
        assert len(guide.steps) == 1
        assert guide.steps[0].title == "外观检查"

    @patch("app.core.guide_generator.get_llm_service")
    @patch("app.core.guide_generator.get_retriever")
    def test_parse_invalid_json(self, mock_retriever, mock_llm):
        """测试无效JSON解析 - 应该抛出异常"""
        generator = GuideGenerator()
        response = "这不是有效的JSON格式"
        with pytest.raises(ValueError):
            guide = generator._parse_guide_response(response)

    @patch("app.core.guide_generator.get_llm_service")
    @patch("app.core.guide_generator.get_retriever")
    def test_check_compliance_basic(self, mock_retriever, mock_llm):
        """测试合规校验基础功能"""
        generator = GuideGenerator()
        # 确保所有字段都是字符串类型
        guide = WorkGuide(
            title="高压开关柜检修",
            task_summary="对10kV高压开关柜进行定期检修",
            preparation=["确认设备停电", "准备工具"],
            steps=[
                GuideStep(
                    step_number=1,
                    title="外观检查",
                    description="检查开关柜外观是否有破损",
                    warnings=["注意保持安全距离"]
                )
            ],
            safety_notes=["全程佩戴安全帽", "确认设备已停电", "使用验电笔验电"],
            completion_criteria=["外观检查通过", "功能测试通过"],
            references=[{"id": "1", "title": "高压开关柜检修规程"}],
        )
        checks = generator.check_compliance(
            guide=guide,
            task_description="高压开关柜检修",
            equipment_type="高压开关柜",
            safety_level="high",
        )
        assert checks is not None
        assert isinstance(checks, list)

    @patch("app.core.guide_generator.get_llm_service")
    @patch("app.core.guide_generator.get_retriever")
    def test_generate_personalized_tips(self, mock_retriever, mock_llm):
        """测试个性化推送生成"""
        generator = GuideGenerator()
        tips = generator.generate_personalized_tips(
            equipment_type="变压器",
            safety_level="high",
            detail_level="detailed",
        )
        assert tips is not None
        assert isinstance(tips, list)

    @patch("app.core.guide_generator.get_llm_service")
    @patch("app.core.guide_generator.get_retriever")
    def test_fallback_mock_response(self, mock_retriever, mock_llm):
        """测试Mock模式降级返回JSON字符串"""
        generator = GuideGenerator()
        response = generator._fallback_mock_response("检修变压器")
        assert response is not None
        # _fallback_mock_response 返回的是 JSON 字符串
        import json
        data = json.loads(response)
        assert "title" in data
        assert "steps" in data
        # 需要通过 _parse_guide_response 解析
        guide = generator._parse_guide_response(response)
        assert guide is not None
        assert hasattr(guide, "title")
        assert len(guide.steps) > 0


class TestGuideGeneratorSafetyLevels:
    """GuideGenerator安全等级测试类"""

    @patch("app.core.guide_generator.get_llm_service")
    @patch("app.core.guide_generator.get_retriever")
    def test_low_safety_level(self, mock_retriever, mock_llm):
        """测试低安全等级"""
        generator = GuideGenerator()
        prompt = generator._build_guide_prompt(
            task_description="清洁维护",
            safety_level="low",
            detail_level="brief",
            knowledge_context="",
        )
        assert "low" in prompt.lower() or "一般" in prompt

    @patch("app.core.guide_generator.get_llm_service")
    @patch("app.core.guide_generator.get_retriever")
    def test_critical_safety_level(self, mock_retriever, mock_llm):
        """测试极高安全等级"""
        generator = GuideGenerator()
        prompt = generator._build_guide_prompt(
            task_description="高压带电作业",
            safety_level="critical",
            detail_level="detailed",
            knowledge_context="",
        )
        assert "critical" in prompt.lower() or "特高" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])