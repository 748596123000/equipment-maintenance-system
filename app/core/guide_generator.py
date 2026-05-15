"""
作业指引生成模块

基于RAG技术生成结构化的设备检修作业指引：
- 根据任务描述检索相关知识
- 结合设备信息生成步骤化指引
- 包含安全警告、工具清单、注意事项等
- 支持多种详细程度输出
- 强调安全注意事项和合规校验
"""

import json
import logging
from typing import Generator, List, Optional

from app.config import settings
from app.services.llm_service import get_llm_service
from app.core.retriever import get_retriever, KnowledgeRetriever

logger = logging.getLogger(__name__)


class GuideStep:
    """作业步骤"""

    def __init__(
        self,
        step_number: int,
        title: str,
        description: str,
        warnings: Optional[List[str]] = None,
        tools_required: Optional[List[str]] = None,
        estimated_time: Optional[str] = None,
        tips: Optional[List[str]] = None,
    ):
        self.step_number = step_number
        self.title = title
        self.description = description
        self.warnings = warnings or []
        self.tools_required = tools_required or []
        self.estimated_time = estimated_time
        self.tips = tips or []

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "step_number": self.step_number,
            "title": self.title,
            "description": self.description,
            "warnings": self.warnings,
            "tools_required": self.tools_required,
            "estimated_time": self.estimated_time,
            "tips": self.tips,
        }


class WorkGuide:
    """作业指引"""

    def __init__(
        self,
        title: str,
        task_summary: str,
        preparation: List[str],
        steps: List[GuideStep],
        safety_notes: List[str],
        completion_criteria: List[str],
        references: List[dict],
    ):
        self.title = title
        self.task_summary = task_summary
        self.preparation = preparation
        self.steps = steps
        self.safety_notes = safety_notes
        self.completion_criteria = completion_criteria
        self.references = references

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "title": self.title,
            "task_summary": self.task_summary,
            "preparation": self.preparation,
            "steps": [step.to_dict() for step in self.steps],
            "safety_notes": self.safety_notes,
            "completion_criteria": self.completion_criteria,
            "references": self.references,
        }


class GuideGenerator:
    """
    作业指引生成器

    基于大模型和知识库检索，生成结构化的设备检修作业指引。
    输出格式规范，包含完整的步骤、安全警告和完成标准。
    强调安全注意事项和合规校验。
    """

    # 作业指引生成的系统提示词
    GUIDE_SYSTEM_PROMPT = """你是一个专业的设备检修作业指引生成专家。根据提供的设备信息和检修知识，生成详细的作业指引。

**重要安全要求：**
- 每个涉及安全风险的步骤必须包含明确的安全警告
- 高风险作业（涉及高压、高空、有毒有害环境等）必须强调安全防护措施
- 所有操作必须符合相关安全规程和行业标准
- 必须包含个人防护装备（PPE）要求
- 涉及停电、动火等特殊作业必须注明审批流程

请严格按照以下JSON格式输出：
{{
    "title": "作业指引标题（包含设备型号和作业类型）",
    "task_summary": "任务概述（2-3句话，说明作业目的和范围）",
    "preparation": [
        "准备工作1（如：确认设备已停电并挂接地线）",
        "准备工作2（如：准备所需工具和材料）",
        "准备工作3（如：办理工作票和安全交底）"
    ],
    "steps": [
        {{
            "step_number": 1,
            "title": "步骤标题（简洁明确）",
            "description": "详细操作描述（包含具体参数、标准和注意事项）",
            "warnings": ["安全警告1（如有安全风险必须填写）"],
            "tools_required": ["所需工具1", "所需工具2"],
            "estimated_time": "预计耗时（如：30分钟）",
            "tips": ["操作提示1（提高效率或质量的建议）"]
        }}
    ],
    "safety_notes": [
        "安全注意事项1（必须包含PPE要求）",
        "安全注意事项2（必须包含应急处理措施）",
        "安全注意事项3（涉及特殊作业的审批要求）"
    ],
    "completion_criteria": [
        "完成标准1（可验证的验收条件）",
        "完成标准2（功能测试要求）"
    ]
}}

安全等级说明：
- low: 一般维护作业（如清洁、检查、润滑）
- standard: 常规检修作业（如更换零部件、调整参数）
- high: 高风险作业（涉及高压、高空、密闭空间等）
- critical: 特高风险作业（涉及停电、动火、有毒有害环境等）

详细程度说明：
- brief: 简要指引（3-5个步骤，适合经验丰富的操作人员）
- medium: 标准指引（5-10个步骤，适合一般操作人员）
- detailed: 详细指引（10-20个步骤，包含更多细节和注意事项，适合新手）

合规要求：
- 所有电气作业必须遵循停电、验电、挂接地线、悬挂标示牌的安全规程
- 涉及特种设备的作业必须由持证人员操作
- 作业完成后必须进行验收和记录
"""

    def __init__(
        self,
        llm_service=None,
        retriever: Optional[KnowledgeRetriever] = None,
    ):
        """
        初始化作业指引生成器

        Args:
            llm_service: LLM服务实例（不提供则使用全局单例）
            retriever: 检索引擎实例（不提供则使用全局单例）
        """
        self.llm_service = llm_service or get_llm_service()
        self.retriever = retriever or get_retriever()

    def generate(
        self,
        task_description: str,
        device_model: Optional[str] = None,
        fault_type: Optional[str] = None,
        safety_level: str = "standard",
        detail_level: str = "medium",
        equipment_type: Optional[str] = None,
        work_environment: Optional[str] = None,
    ) -> WorkGuide:
        """
        生成作业指引

        根据任务描述和设备信息，检索相关知识后生成结构化作业指引。

        Args:
            task_description: 作业任务描述
            device_model: 设备型号
            fault_type: 故障类型（可选）
            safety_level: 安全等级 (low/standard/high/critical)
            detail_level: 详细程度 (brief/medium/detailed)
            equipment_type: 设备类型（可选）
            work_environment: 作业环境（可选）

        Returns:
            WorkGuide: 生成的结构化作业指引
        """
        # 步骤1: 检索相关知识
        knowledge_context = self._retrieve_context(
            task_description=task_description,
            device_model=device_model,
            fault_type=fault_type,
            equipment_type=equipment_type,
        )

        # 步骤2: 构建提示词
        user_prompt = self._build_guide_prompt(
            task_description=task_description,
            equipment_model=device_model,
            equipment_type=equipment_type,
            fault_type=fault_type,
            work_environment=work_environment,
            safety_level=safety_level,
            detail_level=detail_level,
            knowledge_context=knowledge_context,
        )

        # 步骤3: 调用LLM生成
        messages = [
            {"role": "system", "content": self.GUIDE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = self.llm_service.chat(messages, temperature=0.3)
        except Exception as e:
            logger.error(f"LLM调用失败: {e}", exc_info=True)
            raise RuntimeError(f"作业指引生成失败: {str(e)}")

        # 步骤4: 解析响应
        guide = self._parse_guide_response(response)

        # 步骤5: 补充来源引用
        guide.references = self._build_references(knowledge_context)

        logger.info(f"作业指引生成成功: {guide.title}, 共 {len(guide.steps)} 个步骤")
        return guide

    def stream_generate(
        self,
        task_description: str,
        device_model: Optional[str] = None,
        fault_type: Optional[str] = None,
        safety_level: str = "standard",
        detail_level: str = "medium",
        equipment_type: Optional[str] = None,
        work_environment: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        流式生成作业指引

        先检索知识，然后流式生成指引内容。

        Args:
            task_description: 作业任务描述
            其他参数同 generate 方法

        Yields:
            str: 逐步生成的文本片段
        """
        # 检索相关知识
        knowledge_context = self._retrieve_context(
            task_description=task_description,
            device_model=device_model,
            fault_type=fault_type,
            equipment_type=equipment_type,
        )

        # 构建提示词
        user_prompt = self._build_guide_prompt(
            task_description=task_description,
            equipment_model=device_model,
            equipment_type=equipment_type,
            fault_type=fault_type,
            work_environment=work_environment,
            safety_level=safety_level,
            detail_level=detail_level,
            knowledge_context=knowledge_context,
        )

        messages = [
            {"role": "system", "content": self.GUIDE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            for chunk in self.llm_service.stream_chat(messages, temperature=0.3):
                yield chunk
        except Exception as e:
            logger.error(f"流式生成作业指引失败: {e}", exc_info=True)
            yield f"\n\n生成过程中出现错误: {str(e)}"

    def _retrieve_context(
        self,
        task_description: str,
        device_model: Optional[str] = None,
        fault_type: Optional[str] = None,
        equipment_type: Optional[str] = None,
    ) -> str:
        """
        检索相关知识

        根据任务描述、设备型号和故障类型，从知识库中检索相关内容。

        Args:
            task_description: 任务描述
            device_model: 设备型号
            fault_type: 故障类型
            equipment_type: 设备类型

        Returns:
            str: 检索到的知识上下文文本
        """
        context_parts = []

        # 构建检索查询
        query_parts = [task_description]
        if device_model:
            query_parts.append(device_model)
        if fault_type:
            query_parts.append(fault_type)
        if equipment_type:
            query_parts.append(equipment_type)

        query = " ".join(query_parts)

        try:
            # 使用混合检索获取相关知识
            results = self.retriever.hybrid_search(
                query=query,
                top_k=settings.TOP_K_RESULTS,
            )

            if results:
                for i, result in enumerate(results, 1):
                    source = result.source or "未知来源"
                    content = result.content
                    page = result.page_number

                    part = f"[{i}] 来源: {source}"
                    if page:
                        part += f" (第{page}页)"
                    part += f"\n{content}\n"

                    context_parts.append(part)

                logger.info(f"检索到 {len(results)} 条相关知识")

        except Exception as e:
            logger.error(f"知识检索失败: {e}", exc_info=True)

        if not context_parts:
            return "（未检索到相关知识，将基于通用知识生成指引）"

        return "\n".join(context_parts)

    def _build_guide_prompt(
        self,
        task_description: str,
        equipment_model: Optional[str] = None,
        equipment_type: Optional[str] = None,
        fault_type: Optional[str] = None,
        work_environment: Optional[str] = None,
        safety_level: str = "standard",
        detail_level: str = "medium",
        knowledge_context: str = "",
    ) -> str:
        """
        构建作业指引生成的提示词

        Args:
            task_description: 任务描述
            equipment_model: 设备型号
            equipment_type: 设备类型
            fault_type: 故障类型
            work_environment: 作业环境
            safety_level: 安全等级
            detail_level: 详细程度
            knowledge_context: 知识库上下文

        Returns:
            str: 完整的用户提示词
        """
        prompt_parts = [
            "请根据以下信息生成设备检修作业指引：",
            "",
            f"## 作业任务",
            task_description,
        ]

        if equipment_model:
            prompt_parts.append(f"\n## 设备型号\n{equipment_model}")
        if equipment_type:
            prompt_parts.append(f"\n## 设备类型\n{equipment_type}")
        if fault_type:
            prompt_parts.append(f"\n## 故障类型\n{fault_type}")
        if work_environment:
            prompt_parts.append(f"\n## 作业环境\n{work_environment}")

        prompt_parts.append(f"\n## 安全等级\n{safety_level}")
        prompt_parts.append(f"\n## 详细程度\n{detail_level}")

        # 安全等级特别说明
        safety_instructions = {
            "low": "一般维护作业，注意基本安全防护。",
            "standard": "常规检修作业，确保遵守标准操作规程，注意用电安全。",
            "high": "高风险作业！必须严格执行安全规程：办理工作票、安全交底、专人监护。涉及高压作业必须停电验电挂接地线。涉及高空作业必须系安全带。",
            "critical": "特高风险作业！必须执行以下安全措施：1)办理一级工作票；2)编写安全施工方案；3)安全交底和风险评估；4)专人监护；5)应急措施准备；6)作业完成后验收确认。",
        }
        if safety_level in safety_instructions:
            prompt_parts.append(f"\n## 安全要求\n{safety_instructions[safety_level]}")

        if knowledge_context:
            prompt_parts.append(f"\n## 相关知识\n{knowledge_context}")

        prompt_parts.append(
            "\n\n请严格按照JSON格式输出作业指引，确保包含完整的安全注意事项和工具清单。"
        )

        return "\n".join(prompt_parts)

    def _parse_guide_response(self, response: str) -> WorkGuide:
        """
        解析大模型返回的JSON格式作业指引

        支持多种JSON格式（纯JSON、markdown代码块包裹的JSON等）。

        Args:
            response: 大模型返回的文本

        Returns:
            WorkGuide: 结构化的作业指引

        Raises:
            ValueError: JSON解析失败时抛出
        """
        # 提取JSON内容
        json_str = response.strip()

        # 尝试从markdown代码块中提取JSON
        if "```json" in json_str:
            start = json_str.index("```json") + 7
            end = json_str.index("```", start)
            json_str = json_str[start:end].strip()
        elif "```" in json_str:
            start = json_str.index("```") + 3
            end = json_str.index("```", start)
            json_str = json_str[start:end].strip()

        # 尝试找到JSON对象的起始和结束位置
        json_start = json_str.find("{")
        json_end = json_str.rfind("}")
        if json_start >= 0 and json_end > json_start:
            json_str = json_str[json_start:json_end + 1]

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 原始内容: {response[:500]}")
            raise ValueError(f"作业指引格式解析失败: {e}")

        # 验证必要字段
        if not isinstance(data, dict):
            raise ValueError("作业指引数据格式错误：期望JSON对象")

        # 构建步骤列表
        steps = []
        for step_data in data.get("steps", []):
            step = GuideStep(
                step_number=step_data.get("step_number", len(steps) + 1),
                title=step_data.get("title", ""),
                description=step_data.get("description", ""),
                warnings=step_data.get("warnings", []),
                tools_required=step_data.get("tools_required", []),
                estimated_time=step_data.get("estimated_time"),
                tips=step_data.get("tips", []),
            )
            steps.append(step)

        # 重新编号步骤（确保连续）
        for i, step in enumerate(steps):
            step.step_number = i + 1

        # 收集所有工具（去重）
        all_tools = []
        seen_tools = set()
        for step in steps:
            for tool in step.tools_required:
                if tool and tool not in seen_tools:
                    all_tools.append(tool)
                    seen_tools.add(tool)

        # 构建作业指引
        guide = WorkGuide(
            title=data.get("title", "设备检修作业指引"),
            task_summary=data.get("task_summary", ""),
            preparation=data.get("preparation", []),
            steps=steps,
            safety_notes=data.get("safety_notes", []),
            completion_criteria=data.get("completion_criteria", []),
            references=[],
        )

        # 确保安全等级为critical或high时，安全注意事项不为空
        if not guide.safety_notes:
            guide.safety_notes = [
                "作业前必须进行安全交底",
                "必须穿戴规定的个人防护装备",
                "作业完成后必须清理现场并验收",
            ]

        return guide

    def _build_references(self, knowledge_context: str) -> List[dict]:
        """
        从知识上下文中构建来源引用

        Args:
            knowledge_context: 知识上下文文本

        Returns:
            List[dict]: 来源引用列表
        """
        references = []
        if not knowledge_context or knowledge_context.startswith("（未检索到"):
            return references

        # 从上下文中提取来源信息
        import re
        source_pattern = r'\[(\d+)\]\s*来源:\s*([^\n]+)'
        matches = re.findall(source_pattern, knowledge_context)

        for idx, source in matches:
            references.append({
                "index": int(idx),
                "source": source.strip(),
            })

        return references


# 全局作业指引生成器单例
_guide_generator_instance: Optional[GuideGenerator] = None


def get_guide_generator() -> GuideGenerator:
    """获取全局作业指引生成器实例"""
    global _guide_generator_instance
    if _guide_generator_instance is None:
        _guide_generator_instance = GuideGenerator()
    return _guide_generator_instance
