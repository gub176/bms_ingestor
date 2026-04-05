from fastapi import APIRouter, HTTPException, status, Body
from typing import Optional
from pydantic import BaseModel, Field
from app.services.threshold_service import threshold_service
from app.core.exceptions import ThresholdNotFoundException

router = APIRouter(prefix="/thresholds", tags=["thresholds"])


class UpdateThresholdRequest(BaseModel):
    over_voltage: Optional[float] = None
    under_voltage: Optional[float] = None
    over_current: Optional[float] = None
    over_temperature: Optional[float] = None


class CreateTemplateRequest(BaseModel):
    name: str = Field(..., description="模板名称")
    description: Optional[str] = None
    over_voltage: Optional[float] = None
    under_voltage: Optional[float] = None
    over_current: Optional[float] = None
    over_temperature: Optional[float] = None
    is_default: bool = False


@router.get("/{device_id}")
async def get_thresholds(device_id: str):
    """获取设备阈值配置"""
    try:
        result = await threshold_service.get_thresholds(device_id)
        return result
    except ThresholdNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message, "details": e.details}
        )


@router.patch("/{device_id}")
async def update_thresholds(device_id: str, request: UpdateThresholdRequest):
    """更新设备阈值配置"""
    result = await threshold_service.update_thresholds(
        device_id=device_id,
        over_voltage=request.over_voltage,
        under_voltage=request.under_voltage,
        over_current=request.over_current,
        over_temperature=request.over_temperature
    )
    return {"message": "阈值配置已更新", "thresholds": result}


@router.get("/templates")
async def get_templates():
    """获取阈值模板列表"""
    return await threshold_service.get_templates()


@router.post("/templates")
async def create_template(request: CreateTemplateRequest):
    """创建阈值模板"""
    result = await threshold_service.create_template(
        name=request.name,
        description=request.description,
        over_voltage=request.over_voltage,
        under_voltage=request.under_voltage,
        over_current=request.over_current,
        over_temperature=request.over_temperature,
        is_default=request.is_default
    )
    return {"message": "阈值模板已创建", "template": result}


@router.post("/templates/{template_id}/apply/{device_id}")
async def apply_template_to_device(template_id: str, device_id: str):
    """应用阈值模板到设备"""
    result = await threshold_service.apply_template_to_device(template_id, device_id)
    return {"message": "模板已应用到设备", "thresholds": result}
