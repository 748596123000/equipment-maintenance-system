"""
风险评估接口

提供设备检修风险评估功能：
- POST /risk/assess - 执行风险评估
- GET /risk/stream - SSE流式风险评估
- GET /risk/cases - 获取相似历史案例
- POST /risk/compliance-check - 合规性校验
- POST /risk/enhance-guide - 增强作业指引风险警告
"""

import json
import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.models.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


class RiskAssessRequest(BaseModel):
    """风险评估请求"""
    task_description: str = Field(..., min_length=1, max_length=5000, description="作业任务描述")
    equipment_type: Optional[str] = Field(default=None, description="设备类型")
    equipment_model: Optional[str] = Field(default=None, description="设备型号")
    operation_type: Optional[str] = Field(default=None, description="操作类型")
    work_environment: Optional[str] = Field(default=None, description="工作环境")


@router.post("/assess", summary="执行风险评估")
async def assess_risk(request: RiskAssessRequest):
    """
    对设备检修作业进行全面的风险评估

    系统将：
    1. 分析任务描述和设备类型
    2. 识别风险因素并计算风险分数
    3. 检索相似历史事故案例
    4. 生成风险警告和安全措施
    5. 检查合规性要求
    6. 提供操作人员资质要求

    Args:
        request: 风险评估请求

    Returns:
        dict: 风险评估结果
    """
    try:
        from app.core.risk_assessment import WorkGuideRiskAssessment, RiskLevel
        
        assessor = WorkGuideRiskAssessment()
        
        # 执行风险评估
        result = assessor.assess_risk(
            task_description=request.task_description,
            equipment_type=request.equipment_type,
            equipment_model=request.equipment_model,
            operation_type=request.operation_type,
            work_environment=request.work_environment,
        )

        return {
            "code": 200,
            "message": "风险评估完成",
            "data": result.to_dict(),
        }

    except Exception as e:
        logger.error(f"风险评估失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="风险评估失败，请稍后重试")


@router.get("/stream", summary="SSE流式风险评估")
async def stream_assess_risk(
    task_description: str = Query(..., min_length=1, description="作业任务描述"),
    equipment_type: Optional[str] = Query(default=None, description="设备类型"),
    equipment_model: Optional[str] = Query(default=None, description="设备型号"),
    operation_type: Optional[str] = Query(default=None, description="操作类型"),
    work_environment: Optional[str] = Query(default=None, description="工作环境"),
):
    """
    SSE流式风险评估，逐步返回评估过程和结果

    适用于前端需要实时展示评估过程的场景。

    Args:
        task_description: 作业任务描述
        equipment_type: 设备类型
        equipment_model: 设备型号
        operation_type: 操作类型
        work_environment: 工作环境

    Returns:
        StreamingResponse: SSE流式响应
    """
    async def generate_stream():
        """SSE事件流生成器"""
        try:
            from app.core.risk_assessment import WorkGuideRiskAssessment
            
            assessor = WorkGuideRiskAssessment()

            # 发送开始信号
            yield f"data: {json.dumps({'type': 'start', 'message': '开始风险评估...'})}\n\n"

            # 流式执行评估
            for chunk in assessor.stream_assess(
                task_description=task_description,
                equipment_type=equipment_type,
                equipment_model=equipment_model,
                operation_type=operation_type,
                work_environment=work_environment,
            ):
                yield chunk

        except Exception as e:
            logger.error(f"流式风险评估失败: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class SimilarCasesRequest(BaseModel):
    """相似案例查询请求"""
    equipment_type: Optional[str] = Field(default=None, description="设备类型")
    operation_type: Optional[str] = Field(default=None, description="操作类型")
    fault_description: Optional[str] = Field(default=None, description="故障描述")
    top_k: int = Field(default=3, ge=1, le=10, description="返回案例数量")


@router.post("/cases", summary="获取相似历史案例")
async def get_similar_cases(request: SimilarCasesRequest):
    """
    检索与当前作业相似的历史事故案例

    这些案例可作为反面教材，帮助操作人员了解风险。

    Args:
        request: 相似案例查询请求

    Returns:
        dict: 相似案例列表
    """
    try:
        from app.core.risk_assessment import WorkGuideRiskAssessment
        
        assessor = WorkGuideRiskAssessment()
        
        cases = assessor.get_similar_cases(
            equipment_type=request.equipment_type,
            operation_type=request.operation_type,
            fault_description=request.fault_description,
            top_k=request.top_k,
        )

        return {
            "code": 200,
            "message": "案例检索完成",
            "data": {
                "cases": [case.to_dict() for case in cases],
                "total": len(cases),
            },
        }

    except Exception as e:
        logger.error(f"案例检索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="案例检索失败，请稍后重试")


class ComplianceCheckRequest(BaseModel):
    """合规性校验请求"""
    task_description: str = Field(..., description="作业任务描述")
    equipment_type: Optional[str] = Field(default=None, description="设备类型")
    operation_type: Optional[str] = Field(default=None, description="操作类型")
    risk_level: str = Field(default="medium", description="风险等级")


@router.post("/compliance-check", summary="合规性校验")
async def compliance_check(request: ComplianceCheckRequest):
    """
    对作业任务进行合规性校验

    检查操作是否符合安全规程和法规要求。

    Args:
        request: 合规性校验请求

    Returns:
        dict: 合规性校验结果
    """
    try:
        from app.core.risk_assessment import WorkGuideRiskAssessment, RiskLevel
        
        assessor = WorkGuideRiskAssessment()
        
        # 转换为RiskLevel枚举
        try:
            level = RiskLevel(request.risk_level.lower())
        except ValueError:
            level = RiskLevel.MEDIUM

        # 执行合规性校验
        compliance_checks = assessor.check_compliance(
            task_description=request.task_description,
            equipment_type=request.equipment_type,
            operation_type=request.operation_type,
            risk_level=level,
        )

        # 获取资质要求
        operator_requirements = assessor.get_operator_requirements(
            operation_type=request.operation_type,
            risk_level=level,
        )

        return {
            "code": 200,
            "message": "校验完成",
            "data": {
                "compliance_checks": compliance_checks,
                "operator_requirements": operator_requirements,
                "total_checks": len(compliance_checks),
                "required_checks": sum(1 for c in compliance_checks if c.get("required")),
            },
        }

    except Exception as e:
        logger.error(f"合规性校验失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="校验失败，请稍后重试")


class EnhanceGuideRequest(BaseModel):
    """增强作业指引请求"""
    guide_content: str = Field(..., description="作业指引内容（JSON格式字符串）")
    task_description: str = Field(..., description="作业任务描述")
    equipment_type: Optional[str] = Field(default=None, description="设备类型")
    equipment_model: Optional[str] = Field(default=None, description="设备型号")
    operation_type: Optional[str] = Field(default=None, description="操作类型")


@router.post("/enhance-guide", summary="增强作业指引风险警告")
async def enhance_guide(request: EnhanceGuideRequest):
    """
    对作业指引进行风险警告增强

    基于风险评估结果，自动为作业指引添加：
    - 风险等级标识
    - 风险警告信息
    - 历史案例警示
    - 合规检查清单
    - 操作人员资质要求

    Args:
        request: 增强作业指引请求

    Returns:
        dict: 增强后的作业指引
    """
    try:
        from app.core.risk_assessment import WorkGuideRiskAssessment
        from app.core.guide_generator import WorkGuide, GuideStep
        
        assessor = WorkGuideRiskAssessment()
        
        # 首先进行风险评估
        risk_result = assessor.assess_risk(
            task_description=request.task_description,
            equipment_type=request.equipment_type,
            equipment_model=request.equipment_model,
            operation_type=request.operation_type,
        )

        # 解析指引内容
        try:
            guide_data = json.loads(request.guide_content)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"指引内容JSON格式错误: {e}")

        # 构建WorkGuide对象
        steps = []
        for s in guide_data.get("steps", []):
            steps.append(GuideStep(
                step_number=s.get("step_number", 0),
                title=s.get("title", ""),
                description=s.get("description", ""),
                warnings=s.get("warnings", []),
                tools_required=s.get("tools_required", []),
                estimated_time=s.get("estimated_time"),
                tips=s.get("tips", []),
            ))

        guide = WorkGuide(
            title=guide_data.get("title", ""),
            task_summary=guide_data.get("task_summary", ""),
            preparation=guide_data.get("preparation", []),
            steps=steps,
            safety_notes=guide_data.get("safety_notes", []),
            completion_criteria=guide_data.get("completion_criteria", []),
            references=[],
        )

        # 增强指引
        enhanced_guide = assessor.enhance_guide_with_warnings(guide, risk_result)

        return {
            "code": 200,
            "message": "指引增强完成",
            "data": {
                "enhanced_guide": enhanced_guide,
                "risk_assessment": risk_result.to_dict(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"指引增强失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="指引增强失败，请稍后重试")


@router.get("/risk-levels", summary="获取风险等级说明")
async def get_risk_levels():
    """
    获取风险等级说明

    Returns:
        dict: 风险等级定义
    """
    from app.core.risk_assessment import RiskLevel

    levels = []
    for level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.EXTREME]:
        levels.append({
            "value": level.value,
            "label": level.label,
            "color": level.color,
            "description": {
                RiskLevel.LOW: "一般维护作业，风险较低",
                RiskLevel.MEDIUM: "常规检修作业，需要注意安全",
                RiskLevel.HIGH: "高风险作业，必须严格执行安全规程",
                RiskLevel.EXTREME: "极高风险作业，必须执行完整安全措施",
            }.get(level, ""),
        })

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "levels": levels,
        },
    }


@router.get("/equipment-risks", summary="获取设备类型风险配置")
async def get_equipment_risks():
    """
    获取各设备类型的风险配置信息

    Returns:
        dict: 设备类型风险配置
    """
    from app.core.risk_assessment import WorkGuideRiskAssessment

    assessor = WorkGuideRiskAssessment()
    
    equipment_configs = []
    for eq_type, config in assessor.EQUIPMENT_RISK_CONFIG.items():
        equipment_configs.append({
            "equipment_type": eq_type,
            "base_risk": config.get("base_risk", 0.5),
            "typical_operations": config.get("typical_operations", []),
            "critical_operations": config.get("critical_operations", []),
        })

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "equipment_configs": equipment_configs,
        },
    }