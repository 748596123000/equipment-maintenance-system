"""
设备检修风险评估模块

基于设备类型、操作类型和环境因素自动评估风险等级：
- 根据设备类型和操作类型自动评估风险等级（低/中/高/极高）
- 关联历史事故案例，返回相似事故作为反面教材
- 对接 guide_generator.py，提供风险警告增强
- 提供合规性校验（检查操作人员资质要求）
- 支持流式输出（SSE）
"""

import json
import logging
from enum import Enum
from typing import Dict, Generator, List, Optional, Any
from dataclasses import dataclass, field

from app.config import settings
from app.services.llm_service import get_llm_service
from app.core.retriever import get_retriever, SearchResult
from app.utils.helpers import extract_json_from_text

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """风险等级枚举"""
    LOW = "low"          # 低风险
    MEDIUM = "medium"    # 中风险
    HIGH = "high"        # 高风险
    EXTREME = "extreme"  # 极高风险

    @classmethod
    def from_score(cls, score: float) -> "RiskLevel":
        """根据风险分数返回风险等级"""
        if score < 0.3:
            return cls.LOW
        elif score < 0.6:
            return cls.MEDIUM
        elif score < 0.8:
            return cls.HIGH
        else:
            return cls.EXTREME

    @property
    def color(self) -> str:
        """风险等级颜色"""
        colors = {
            RiskLevel.LOW: "#22c55e",      # 绿色
            RiskLevel.MEDIUM: "#eab308",  # 黄色
            RiskLevel.HIGH: "#f97316",    # 橙色
            RiskLevel.EXTREME: "#ef4444", # 红色
        }
        return colors.get(self, "#6b7280")

    @property
    def label(self) -> str:
        """风险等级标签"""
        labels = {
            RiskLevel.LOW: "低风险",
            RiskLevel.MEDIUM: "中风险",
            RiskLevel.HIGH: "高风险",
            RiskLevel.EXTREME: "极高风险",
        }
        return labels.get(self, "未知")


@dataclass
class RiskFactor:
    """风险因素"""
    name: str                          # 因素名称
    category: str                      # 因素类别（设备、环境、操作、人员）
    score: float                       # 风险分值（0-1）
    description: str                   # 描述
    recommendation: str = ""          # 建议措施


@dataclass
class HistoricalCase:
    """历史事故案例"""
    id: str
    title: str
    description: str
    device_type: str
    fault_type: str
    cause: str                          # 事故原因
    consequence: str                    # 后果
    lessons_learned: str                # 教训
    severity: str                      # 严重程度
    occurred_at: str = ""               # 发生时间

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "device_type": self.device_type,
            "fault_type": self.fault_type,
            "cause": self.cause,
            "consequence": self.consequence,
            "lessons_learned": self.lessons_learned,
            "severity": self.severity,
            "occurred_at": self.occurred_at,
        }


@dataclass
class RiskAssessmentResult:
    """风险评估结果"""
    task_description: str
    equipment_type: str
    equipment_model: str
    operation_type: str
    risk_level: RiskLevel
    risk_score: float
    risk_factors: List[RiskFactor]
    similar_cases: List[HistoricalCase]
    warnings: List[str]
    safety_measures: List[str]
    compliance_checks: List[Dict[str, Any]]
    operator_requirements: Dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "task_description": self.task_description,
            "equipment_type": self.equipment_type,
            "equipment_model": self.equipment_model,
            "operation_type": self.operation_type,
            "risk_level": self.risk_level.value if isinstance(self.risk_level, RiskLevel) else self.risk_level,
            "risk_score": round(self.risk_score, 2),
            "risk_level_label": self.risk_level.label if isinstance(self.risk_level, RiskLevel) else str(self.risk_level),
            "risk_level_color": self.risk_level.color if isinstance(self.risk_level, RiskLevel) else "#6b7280",
            "risk_factors": [
                {
                    "name": f.name,
                    "category": f.category,
                    "score": round(f.score, 2),
                    "description": f.description,
                    "recommendation": f.recommendation,
                }
                for f in self.risk_factors
            ],
            "similar_cases": [c.to_dict() for c in self.similar_cases],
            "warnings": self.warnings,
            "safety_measures": self.safety_measures,
            "compliance_checks": self.compliance_checks,
            "operator_requirements": self.operator_requirements,
        }


class WorkGuideRiskAssessment:
    """
    作业指引风险评估器

    根据设备类型、操作类型和环境因素，自动评估风险等级，
    关联历史事故案例，并对作业指引进行风险警告增强。

    支持流式输出（SSE），方便实时展示评估过程。
    """

    # 设备类型风险配置
    EQUIPMENT_RISK_CONFIG: Dict[str, Dict[str, Any]] = {
        "变压器": {
            "base_risk": 0.5,
            "typical_operations": ["检修", "维护", "加油", "换油"],
            "critical_operations": ["带电操作", "吊装", "内部检修"],
            "keywords": ["变压器", "绕组", "绝缘", "油温", "瓦斯继电器"],
        },
        "断路器": {
            "base_risk": 0.6,
            "typical_operations": ["检修", "试验", "操作"],
            "critical_operations": ["带电操作", "储能机构检修"],
            "keywords": ["断路器", "触头", "操作机构", "储能"],
        },
        "开关柜": {
            "base_risk": 0.6,
            "typical_operations": ["检修", "清扫", "试验"],
            "critical_operations": ["带电操作", "母线检修", "抽屉检修"],
            "keywords": ["开关柜", "母线", "抽屉", "隔离触头"],
        },
        "电缆": {
            "base_risk": 0.5,
            "typical_operations": ["试验", "敷设", "接头制作"],
            "critical_operations": ["带电试验", "挖掘作业"],
            "keywords": ["电缆", "接头", "绝缘", "耐压试验"],
        },
        "电动机": {
            "base_risk": 0.3,
            "typical_operations": ["检修", "维护", "轴承更换"],
            "critical_operations": ["带电操作"],
            "keywords": ["电机", "轴承", "绝缘", "振动"],
        },
        "配电箱": {
            "base_risk": 0.4,
            "typical_operations": ["检修", "清扫", "紧固"],
            "critical_operations": ["带电操作"],
            "keywords": ["配电箱", "空开", "漏电保护器"],
        },
        "架空线路": {
            "base_risk": 0.7,
            "typical_operations": ["巡检", "检修", "更换部件"],
            "critical_operations": ["高空作业", "带电作业"],
            "keywords": ["架空线", "导线", "杆塔", "绝缘子"],
        },
    }

    # 操作类型风险系数
    OPERATION_RISK_FACTORS: Dict[str, float] = {
        # 高风险操作
        "带电操作": 1.5,
        "高压试验": 1.5,
        "带电作业": 1.5,
        "高空作业": 1.4,
        "密闭空间": 1.4,
        "动火作业": 1.4,
        "吊装作业": 1.3,
        "挖掘作业": 1.3,
        "电气试验": 1.3,
        # 中风险操作
        "检修": 1.0,
        "维护": 0.9,
        "清扫": 0.8,
        "巡检": 0.6,
        "加油": 0.8,
        "换油": 0.9,
        "更换": 1.0,
        # 低风险操作
        "测量": 0.5,
        "观察": 0.3,
        "记录": 0.2,
        "紧固": 0.6,
    }

    # 环境风险因素
    ENVIRONMENT_RISK_FACTORS: Dict[str, float] = {
        "高温环境": 1.3,
        "低温环境": 1.2,
        "潮湿环境": 1.3,
        "粉尘环境": 1.2,
        "易燃易爆": 1.5,
        "有毒有害": 1.4,
        "狭窄空间": 1.3,
        "高空作业": 1.4,
        "户外作业": 1.1,
        "夜间作业": 1.2,
    }

    # 操作人员资质要求
    OPERATOR_CERTIFICATIONS: Dict[str, List[Dict[str, Any]]] = {
        "高压电工": [
            {"name": "高压电工证", "description": "从事高压电气设备作业必须持有", "required": True},
        ],
        "低压电工": [
            {"name": "低压电工证", "description": "从事低压电气设备作业必须持有", "required": True},
        ],
        "电气试验": [
            {"name": "高压电工证", "description": "从事高压试验作业必须持有", "required": True},
            {"name": "电气试验操作证", "description": "特定试验项目需要", "required": False},
        ],
        "高空作业": [
            {"name": "高空作业证", "description": "从事2米以上高空作业必须持有", "required": True},
        ],
        "吊装作业": [
            {"name": "吊车操作证", "description": "操作吊车必须持有", "required": True},
            {"name": "起重作业证", "description": "从事吊装指挥必须持有", "required": True},
        ],
        "焊接作业": [
            {"name": "焊工证", "description": "从事焊接作业必须持有", "required": True},
        ],
        "有限空间": [
            {"name": "有限空间作业证", "description": "进入密闭空间作业必须持有", "required": True},
        ],
        "动火作业": [
            {"name": "动火审批证", "description": "进行动火作业前必须审批", "required": True},
        ],
    }

    # 风险警告模板
    RISK_WARNING_TEMPLATES: Dict[RiskLevel, List[str]] = {
        RiskLevel.LOW: [
            "本作业属于低风险作业，但仍需遵守基本安全规程",
            "请穿戴基本防护装备（安全帽、手套）",
        ],
        RiskLevel.MEDIUM: [
            "【中风险作业】请严格执行标准操作规程",
            "必须确认设备断电后方可进行操作",
            "建议佩戴防护装备（安全帽、绝缘手套、护目镜）",
            "作业前进行安全确认",
        ],
        RiskLevel.HIGH: [
            "【高风险作业警告】必须严格执行以下安全措施：",
            "1. 办理工作票和安全交底",
            "2. 设专人监护",
            "3. 佩戴完整防护装备（安全帽、绝缘手套、绝缘鞋、护目镜）",
            "4. 作业前进行风险评估",
            "5. 准备应急救援装备",
        ],
        RiskLevel.EXTREME: [
            "【极高风险作业警告】本作业具有极高危险性，必须执行以下措施：",
            "1. 办理一级工作票",
            "2. 编写安全施工方案",
            "3. 安全交底和风险评估",
            "4. 设专人监护并配备应急装备",
            "5. 佩戴全套防护装备并确认完好",
            "6. 作业前进行安全确认和检查",
            "7. 作业完成后必须验收确认",
            "8. 作业区域设置警戒线和警示标识",
        ],
    }

    def __init__(
        self,
        llm_service=None,
        retriever=None,
    ):
        """
        初始化风险评估器

        Args:
            llm_service: LLM服务实例（不提供则使用全局单例）
            retriever: 检索引擎实例（不提供则使用全局单例）
        """
        self.llm_service = llm_service or get_llm_service()
        self.retriever = retriever or get_retriever()

    def assess_risk(
        self,
        task_description: str,
        equipment_type: Optional[str] = None,
        equipment_model: Optional[str] = None,
        operation_type: Optional[str] = None,
        work_environment: Optional[str] = None,
    ) -> RiskAssessmentResult:
        """
        评估风险等级

        Args:
            task_description: 任务描述
            equipment_type: 设备类型
            equipment_model: 设备型号
            operation_type: 操作类型
            work_environment: 工作环境

        Returns:
            RiskAssessmentResult: 风险评估结果
        """
        # 步骤1: 确定设备类型
        if not equipment_type and task_description:
            equipment_type = self._detect_equipment_type(task_description)

        # 步骤2: 确定操作类型
        if not operation_type and task_description:
            operation_type = self._detect_operation_type(task_description)

        # 步骤3: 计算风险因素
        risk_factors = self._calculate_risk_factors(
            task_description=task_description,
            equipment_type=equipment_type,
            equipment_model=equipment_model,
            operation_type=operation_type,
            work_environment=work_environment,
        )

        # 步骤4: 计算综合风险分数
        risk_score = self._calculate_risk_score(risk_factors)
        risk_level = RiskLevel.from_score(risk_score)

        # 步骤5: 获取相似历史案例
        similar_cases = self.get_similar_cases(
            equipment_type=equipment_type,
            operation_type=operation_type,
            fault_description=task_description,
        )

        # 步骤6: 生成风险警告
        warnings = self._generate_warnings(risk_level, risk_factors)

        # 步骤7: 生成安全措施
        safety_measures = self._generate_safety_measures(risk_level, equipment_type, operation_type)

        # 步骤8: 合规性校验
        compliance_checks = self.check_compliance(
            task_description=task_description,
            equipment_type=equipment_type,
            operation_type=operation_type,
            risk_level=risk_level,
        )

        # 步骤9: 操作人员资质要求
        operator_requirements = self.get_operator_requirements(operation_type, risk_level)

        return RiskAssessmentResult(
            task_description=task_description,
            equipment_type=equipment_type or "通用设备",
            equipment_model=equipment_model or "",
            operation_type=operation_type or "常规操作",
            risk_level=risk_level,
            risk_score=risk_score,
            risk_factors=risk_factors,
            similar_cases=similar_cases,
            warnings=warnings,
            safety_measures=safety_measures,
            compliance_checks=compliance_checks,
            operator_requirements=operator_requirements,
        )

    def stream_assess(
        self,
        task_description: str,
        equipment_type: Optional[str] = None,
        equipment_model: Optional[str] = None,
        operation_type: Optional[str] = None,
        work_environment: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        流式风险评估

        Args:
            task_description: 任务描述
            其他参数同 assess_risk 方法

        Yields:
            str: 逐步评估的文本片段
        """
        # 步骤1: 确定设备类型
        if not equipment_type and task_description:
            yield f"data: {json.dumps({'type': 'step', 'step': 'detecting_equipment', 'message': '正在分析设备类型...'})}\n\n"
            equipment_type = self._detect_equipment_type(task_description)
            yield f"data: {json.dumps({'type': 'equipment_detected', 'equipment_type': equipment_type})}\n\n"

        # 步骤2: 确定操作类型
        if not operation_type and task_description:
            yield f"data: {json.dumps({'type': 'step', 'step': 'detecting_operation', 'message': '正在分析操作类型...'})}\n\n"
            operation_type = self._detect_operation_type(task_description)
            yield f"data: {json.dumps({'type': 'operation_detected', 'operation_type': operation_type})}\n\n"

        # 步骤3: 计算风险因素
        yield f"data: {json.dumps({'type': 'step', 'step': 'calculating_risk', 'message': '正在计算风险因素...'})}\n\n"
        risk_factors = self._calculate_risk_factors(
            task_description=task_description,
            equipment_type=equipment_type,
            equipment_model=equipment_model,
            operation_type=operation_type,
            work_environment=work_environment,
        )
        yield f"data: {json.dumps({'type': 'risk_factors', 'factors': [f.to_dict() for f in risk_factors]})}\n\n"

        # 步骤4: 计算综合风险分数
        yield f"data: {json.dumps({'type': 'step', 'step': 'scoring', 'message': '正在计算综合风险分数...'})}\n\n"
        risk_score = self._calculate_risk_score(risk_factors)
        risk_level = RiskLevel.from_score(risk_score)
        yield f"data: {json.dumps({'type': 'risk_scored', 'score': round(risk_score, 2), 'level': risk_level.value, 'level_label': risk_level.label})}\n\n"

        # 步骤5: 获取相似历史案例
        yield f"data: {json.dumps({'type': 'step', 'step': 'fetching_cases', 'message': '正在检索相似历史案例...'})}\n\n"
        similar_cases = self.get_similar_cases(
            equipment_type=equipment_type,
            operation_type=operation_type,
            fault_description=task_description,
        )
        yield f"data: {json.dumps({'type': 'cases_found', 'count': len(similar_cases)})}\n\n"

        # 步骤6: 生成警告和措施
        yield f"data: {json.dumps({'type': 'step', 'step': 'generating_warnings', 'message': '正在生成风险警告...'})}\n\n"
        warnings = self._generate_warnings(risk_level, risk_factors)
        safety_measures = self._generate_safety_measures(risk_level, equipment_type, operation_type)
        compliance_checks = self.check_compliance(
            task_description=task_description,
            equipment_type=equipment_type,
            operation_type=operation_type,
            risk_level=risk_level,
        )
        operator_requirements = self.get_operator_requirements(operation_type, risk_level)

        # 最终结果
        result = RiskAssessmentResult(
            task_description=task_description,
            equipment_type=equipment_type or "通用设备",
            equipment_model=equipment_model or "",
            operation_type=operation_type or "常规操作",
            risk_level=risk_level,
            risk_score=risk_score,
            risk_factors=risk_factors,
            similar_cases=similar_cases,
            warnings=warnings,
            safety_measures=safety_measures,
            compliance_checks=compliance_checks,
            operator_requirements=operator_requirements,
        )
        yield f"data: {json.dumps({'type': 'complete', 'result': result.to_dict()})}\n\n"

    def _detect_equipment_type(self, task_description: str) -> str:
        """检测设备类型"""
        text = task_description.lower()
        for eq_type, config in self.EQUIPMENT_RISK_CONFIG.items():
            keywords = config.get("keywords", [])
            if any(kw.lower() in text for kw in keywords):
                return eq_type
        return "通用设备"

    def _detect_operation_type(self, task_description: str) -> str:
        """检测操作类型"""
        text = task_description.lower()
        
        # 按关键字长度降序排列，优先匹配更长的关键字
        operation_types = sorted(
            self.OPERATION_RISK_FACTORS.keys(),
            key=len,
            reverse=True
        )
        
        for op_type in operation_types:
            if op_type.lower() in text:
                return op_type
        return "检修"

    def _calculate_risk_factors(
        self,
        task_description: str,
        equipment_type: Optional[str] = None,
        equipment_model: Optional[str] = None,
        operation_type: Optional[str] = None,
        work_environment: Optional[str] = None,
    ) -> List[RiskFactor]:
        """计算风险因素"""
        factors = []
        text = task_description.lower()

        # 设备类型风险
        if equipment_type:
            config = self.EQUIPMENT_RISK_CONFIG.get(equipment_type)
            if config:
                base_risk = config.get("base_risk", 0.5)
                factors.append(RiskFactor(
                    name=f"{equipment_type}检修",
                    category="设备",
                    score=base_risk,
                    description=f"{equipment_type}基础风险系数",
                    recommendation=f"针对{equipment_type}作业请严格遵守专业规程",
                ))

        # 操作类型风险
        if operation_type:
            op_score = self.OPERATION_RISK_FACTORS.get(operation_type, 1.0)
            factors.append(RiskFactor(
                name=operation_type,
                category="操作",
                score=min(op_score - 0.5, 1.0),
                description=f"{operation_type}风险系数: {op_score}",
                recommendation=f"执行{operation_type}时请特别注意安全",
            ))

            # 检查是否为关键操作
            if equipment_type:
                config = self.EQUIPMENT_RISK_CONFIG.get(equipment_type)
                if config:
                    critical_ops = config.get("critical_operations", [])
                    if operation_type in critical_ops:
                        factors.append(RiskFactor(
                            name="关键操作识别",
                            category="操作",
                            score=0.9,
                            description=f"{operation_type}属于{equipment_type}的关键操作",
                            recommendation="此操作必须办理工作票并设专人监护",
                        ))

        # 环境风险
        if work_environment:
            for env, factor in self.ENVIRONMENT_RISK_FACTORS.items():
                if env in work_environment:
                    factors.append(RiskFactor(
                        name=env,
                        category="环境",
                        score=factor - 1.0,
                        description=f"作业环境存在{env}风险",
                        recommendation=f"在{env}下作业需采取相应防护措施",
                    ))

        # 从任务描述中识别风险关键词
        risk_keywords = {
            "高压": (0.8, "涉及高压设备，存在电击风险"),
            "带电": (0.9, "带电作业必须采取绝缘防护措施"),
            "高空": (0.7, "高空作业必须系安全带"),
            "密闭": (0.8, "密闭空间作业必须进行气体检测"),
            "动火": (0.8, "动火作业必须办理动火证并配备灭火器"),
            "吊装": (0.6, "吊装作业必须设专人指挥"),
            "有毒": (0.8, "有毒有害环境必须佩戴防毒面具"),
            "易燃": (0.7, "易燃易爆环境必须禁止明火"),
        }
        for keyword, (score, desc) in risk_keywords.items():
            if keyword in text:
                factors.append(RiskFactor(
                    name=f"风险识别: {keyword}",
                    category="关键词",
                    score=score,
                    description=desc,
                    recommendation="请采取相应安全措施",
                ))

        return factors

    def _calculate_risk_score(self, risk_factors: List[RiskFactor]) -> float:
        """计算综合风险分数"""
        if not risk_factors:
            return 0.3

        # 加权平均计算
        total_weight = 0
        weighted_sum = 0
        for factor in risk_factors:
            # 高风险类别权重更高
            category_weights = {
                "设备": 1.0,
                "操作": 1.2,
                "环境": 0.8,
                "关键词": 1.5,
            }
            weight = category_weights.get(factor.category, 1.0)
            weighted_sum += factor.score * weight
            total_weight += weight

        score = weighted_sum / total_weight if total_weight > 0 else 0.3
        return min(max(score, 0.1), 0.95)

    def get_similar_cases(
        self,
        equipment_type: Optional[str] = None,
        operation_type: Optional[str] = None,
        fault_description: Optional[str] = None,
        top_k: int = 3,
    ) -> List[HistoricalCase]:
        """
        获取相似历史案例

        从数据库中检索与当前作业相似的历史事故案例，作为反面教材。

        Args:
            equipment_type: 设备类型
            operation_type: 操作类型
            fault_description: 故障描述
            top_k: 返回案例数量

        Returns:
            List[HistoricalCase]: 相似案例列表
        """
        # 构建检索查询
        query_parts = []
        if equipment_type:
            query_parts.append(equipment_type)
        if operation_type:
            query_parts.append(operation_type)
        if fault_description:
            query_parts.append(fault_description)

        query = " ".join(query_parts) if query_parts else "设备检修事故"

        try:
            # 从知识库检索相关案例
            results = self.retriever.hybrid_search(
                query=query,
                top_k=top_k,
            )

            cases = []
            for result in results[:top_k]:
                # 解析检索结果为案例
                if hasattr(result, "content"):
                    content = result.content
                    source = getattr(result, "source", "历史案例")
                elif isinstance(result, dict):
                    content = result.get("content", "")
                    source = result.get("source", "历史案例")
                else:
                    continue

                # 构建案例对象
                case = HistoricalCase(
                    id=f"case_{hash(content) % 100000}",
                    title=f"历史案例: {source}",
                    description=content[:200] + "..." if len(content) > 200 else content,
                    device_type=equipment_type or "通用",
                    fault_type=operation_type or "未知",
                    cause="根据相似案例分析，可能的事故原因包括操作不当、设备缺陷等",
                    consequence="可能导致设备损坏、人员伤亡等严重后果",
                    lessons_learned=self._extract_lessons(content),
                    severity=self._estimate_severity(content),
                )
                cases.append(case)

            # 如果检索不到案例，返回一些示例案例
            if not cases:
                cases = self._get_sample_cases(equipment_type, operation_type)

        except Exception as e:
            logger.error(f"检索相似案例失败: {e}", exc_info=True)
            cases = self._get_sample_cases(equipment_type, operation_type)

        return cases

    def _extract_lessons(self, content: str) -> str:
        """从案例内容中提取教训"""
        # 简化实现，实际可以从LLM生成
        if "教训" in content:
            return content[content.find("教训"):].split("\n")[0]
        return "请严格按照操作规程作业，避免类似事故再次发生"

    def _estimate_severity(self, content: str) -> str:
        """评估严重程度"""
        if "伤亡" in content or "死亡" in content:
            return "严重"
        elif "损坏" in content or "故障" in content:
            return "较重"
        return "一般"

    def _get_sample_cases(
        self,
        equipment_type: Optional[str] = None,
        operation_type: Optional[str] = None,
    ) -> List[HistoricalCase]:
        """获取示例案例（当检索不到时使用）"""
        sample_cases = [
            HistoricalCase(
                id="sample_001",
                title="变压器带电检修触电事故",
                description="某电站在进行变压器带电检修时，因未严格执行停电程序，操作人员触电身亡",
                device_type="变压器",
                fault_type="带电操作",
                cause="违反操作规程，未停电就进行检修",
                consequence="操作人员触电身亡",
                lessons_learned="带电作业必须严格遵守停电、验电、接地程序，操作前必须确认设备已断电",
                severity="严重",
                occurred_at="2023-05-15",
            ),
            HistoricalCase(
                id="sample_002",
                title="高空作业坠落事故",
                description="某工人在进行架空线路检修时，因未系安全带，从电杆上坠落受伤",
                device_type="架空线路",
                fault_type="高空作业",
                cause="作业人员未按规定佩戴安全带，安全意识薄弱",
                consequence="作业人员坠落受伤",
                lessons_learned="高空作业必须系好安全带，高挂低用，严禁不系安全带作业",
                severity="严重",
                occurred_at="2023-08-22",
            ),
            HistoricalCase(
                id="sample_003",
                title="开关柜内部短路事故",
                description="某配电室在进行开关柜检修时，因未清理现场工具，导致开关柜内部短路",
                device_type="开关柜",
                fault_type="检修",
                cause="检修后未清理现场，工具遗留在开关柜内",
                consequence="开关柜短路损坏，造成区域停电",
                lessons_learned="检修完成后必须清点工具，确认现场无遗留物后方可送电",
                severity="较重",
                occurred_at="2024-01-10",
            ),
        ]

        # 根据设备类型过滤
        if equipment_type:
            filtered = [c for c in sample_cases if c.device_type == equipment_type]
            if filtered:
                return filtered[:2]

        return sample_cases[:1]

    def _generate_warnings(
        self,
        risk_level: RiskLevel,
        risk_factors: List[RiskFactor],
    ) -> List[str]:
        """生成风险警告"""
        warnings = []

        # 添加基础警告
        base_warnings = self.RISK_WARNING_TEMPLATES.get(risk_level, [])
        warnings.extend(base_warnings)

        # 根据风险因素添加特定警告
        for factor in risk_factors:
            if factor.score > 0.5:
                warnings.append(f"[{factor.category}] {factor.name}: {factor.recommendation}")

        return warnings

    def _generate_safety_measures(
        self,
        risk_level: RiskLevel,
        equipment_type: Optional[str],
        operation_type: Optional[str],
    ) -> List[str]:
        """生成安全措施"""
        measures = []

        # 基础安全措施
        if risk_level in (RiskLevel.HIGH, RiskLevel.EXTREME):
            measures.extend([
                "办理相应工作票",
                "进行安全技术交底",
                "设专人监护",
                "准备好应急救援装备",
            ])

        # 设备特定措施
        if equipment_type:
            specific_measures = {
                "变压器": ["加油前确认瓦斯继电器完好", "换油时注意油温控制"],
                "断路器": ["检修前释放弹簧能量", "确认触头已隔离"],
                "开关柜": ["检修前确认母线无电", "抽屉拉出后锁定"],
                "电缆": ["耐压试验前确认接地良好", "注意试验电压控制"],
                "架空线路": ["登杆前检查杆塔牢固", "使用防坠落装置"],
            }
            if equipment_type in specific_measures:
                measures.extend(specific_measures[equipment_type])

        # 操作特定措施
        if operation_type:
            op_measures = {
                "带电操作": ["使用绝缘工具", "保持安全距离", "穿戴绝缘防护装备"],
                "高空作业": ["系好安全带", "使用安全绳", "设置安全网"],
                "电气试验": ["设置警戒线", "试验时人员撤离", "试验后充分放电"],
            }
            if operation_type in op_measures:
                measures.extend(op_measures[operation_type])

        return list(set(measures))  # 去重

    def check_compliance(
        self,
        task_description: str,
        equipment_type: Optional[str] = None,
        operation_type: Optional[str] = None,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
    ) -> List[Dict[str, Any]]:
        """合规性校验"""
        checks = []
        combined_text = f"{task_description} {equipment_type or ''} {operation_type or ''}"

        # 电气作业合规检查
        electrical_keywords = ["电", "变压器", "开关", "线路", "配电", "电缆"]
        if any(kw in combined_text for kw in electrical_keywords):
            checks.extend([
                {
                    "category": "电气安全",
                    "rule": "停电验电挂接地线",
                    "description": "电气作业前必须停电、验电、挂接地线",
                    "required": True,
                    "status": "pending",
                },
                {
                    "category": "电气安全",
                    "rule": "工作票制度",
                    "description": "必须办理电气工作票，经审批后方可作业",
                    "required": True,
                    "status": "pending",
                },
                {
                    "category": "电气安全",
                    "rule": "专人监护",
                    "description": "电气作业必须设专人监护",
                    "required": risk_level in (RiskLevel.HIGH, RiskLevel.EXTREME),
                    "status": "pending",
                },
            ])

        # 高空作业合规检查
        if "高空" in combined_text or operation_type == "高空作业":
            checks.extend([
                {
                    "category": "高空作业",
                    "rule": "安全带",
                    "description": "高空作业必须系安全带，高挂低用",
                    "required": True,
                    "status": "pending",
                },
                {
                    "category": "高空作业",
                    "rule": "作业审批",
                    "description": "必须办理高空作业审批手续",
                    "required": True,
                    "status": "pending",
                },
            ])

        # 密闭空间合规检查
        if "密闭" in combined_text or "有限空间" in combined_text:
            checks.extend([
                {
                    "category": "有限空间",
                    "rule": "气体检测",
                    "description": "进入前必须进行有害气体检测",
                    "required": True,
                    "status": "pending",
                },
                {
                    "category": "有限空间",
                    "rule": "通风措施",
                    "description": "必须保持持续通风",
                    "required": True,
                    "status": "pending",
                },
            ])

        # 动火作业合规检查
        if "动火" in combined_text or operation_type == "动火作业":
            checks.extend([
                {
                    "category": "动火作业",
                    "rule": "动火审批",
                    "description": "必须办理动火作业许可证",
                    "required": True,
                    "status": "pending",
                },
                {
                    "category": "动火作业",
                    "rule": "消防措施",
                    "description": "动火现场必须配备灭火器材",
                    "required": True,
                    "status": "pending",
                },
            ])

        return checks

    def get_operator_requirements(
        self,
        operation_type: Optional[str] = None,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
    ) -> Dict[str, Any]:
        """获取操作人员资质要求"""
        requirements = {
            "basic": {
                "name": "基本资质",
                "description": "从事设备检修作业必须具备的基本资质",
                "certifications": [
                    {
                        "name": "电工证",
                        "description": "从事电气作业必须持有有效期内的电工证",
                        "required": True,
                    },
                ],
            },
            "additional": [],
        }

        # 根据操作类型添加特定资质要求
        if operation_type:
            operation_mapping = {
                "高空作业": "高空作业",
                "吊装作业": "吊装作业",
                "焊接作业": "焊接作业",
                "带电操作": "高压电工",
                "高压试验": "电气试验",
            }

            required_cert = operation_mapping.get(operation_type)
            if required_cert and required_cert in self.OPERATOR_CERTIFICATIONS:
                cert_list = self.OPERATOR_CERTIFICATIONS[required_cert]
                for cert in cert_list:
                    requirements["additional"].append(cert)

        # 根据风险等级添加额外要求
        if risk_level in (RiskLevel.HIGH, RiskLevel.EXTREME):
            requirements["additional"].append({
                "name": "安全培训合格证",
                "description": "高风险作业人员必须经过安全培训并合格",
                "required": True,
            })
            requirements["additional"].append({
                "name": "应急救援培训",
                "description": "极高风险作业人员必须掌握应急救援技能",
                "required": risk_level == RiskLevel.EXTREME,
            })

        return requirements

    def enhance_guide_with_warnings(
        self,
        guide,
        risk_result: RiskAssessmentResult,
    ) -> dict:
        """
        对作业指引进行风险警告增强

        将风险评估结果整合到作业指引中，增强安全警告信息。

        Args:
            guide: WorkGuide对象
            risk_result: 风险评估结果

        Returns:
            dict: 增强后的指引内容
        """
        guide_dict = guide.to_dict() if hasattr(guide, "to_dict") else guide

        # 添加风险警告到安全注意事项
        risk_warnings = [
            f"【风险等级: {risk_result.risk_level.label}】",
            f"综合风险分数: {risk_result.risk_score:.2f}",
        ]
        for warning in risk_result.warnings[:5]:  # 最多添加5条警告
            risk_warnings.append(warning)

        if "safety_notes" not in guide_dict:
            guide_dict["safety_notes"] = []
        guide_dict["safety_notes"] = risk_warnings + guide_dict["safety_notes"]

        # 为每个步骤添加风险提示
        if "steps" in guide_dict:
            for step in guide_dict["steps"]:
                if "warnings" not in step:
                    step["warnings"] = []
                # 根据风险等级添加通用警告
                if risk_result.risk_level in (RiskLevel.HIGH, RiskLevel.EXTREME):
                    step["warnings"].insert(0, "【高风险步骤】请严格遵守操作规程")

        # 添加历史案例警示
        if risk_result.similar_cases:
            case_warnings = []
            for case in risk_result.similar_cases[:2]:
                case_warnings.append(f"【警示】{case.title} - {case.lessons_learned}")
            guide_dict["risk_warnings"] = case_warnings

        # 添加合规检查清单
        guide_dict["compliance_checklist"] = [
            {
                "rule": check["rule"],
                "description": check["description"],
                "checked": False,
            }
            for check in risk_result.compliance_checks
        ]

        # 添加操作人员资质要求
        guide_dict["operator_requirements"] = risk_result.operator_requirements

        return guide_dict


# 全局风险评估器单例
_risk_assessment_instance: Optional[WorkGuideRiskAssessment] = None


def get_risk_assessment() -> WorkGuideRiskAssessment:
    """获取全局风险评估器实例"""
    global _risk_assessment_instance
    if _risk_assessment_instance is None:
        _risk_assessment_instance = WorkGuideRiskAssessment()
    return _risk_assessment_instance