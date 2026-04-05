from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional
from app.services.device_service import device_service
from app.schemas.device import (
    DeviceListResponse,
    DeviceDetailResponse,
    BindDeviceRequest,
    BindDeviceResponse
)
from app.core.exceptions import DeviceNotFoundException, DeviceAlreadyBoundException

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=DeviceListResponse)
async def get_devices(
    user_id: Optional[str] = Query(None, description="用户 ID"),
    status: Optional[str] = Query(None, description="设备状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序顺序")
):
    """获取设备列表"""
    result = await device_service.get_devices(
        user_id=user_id,
        status=status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return result


@router.get("/{device_id}", response_model=DeviceDetailResponse)
async def get_device_detail(device_id: str, user_id: Optional[str] = Query(None)):
    """获取设备详情"""
    try:
        result = await device_service.get_device_by_id(device_id, user_id)
        return result
    except DeviceNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message, "details": e.details}
        )


@router.post("/bind", response_model=BindDeviceResponse)
async def bind_device(request: BindDeviceRequest):
    """绑定设备"""
    try:
        device = await device_service.bind_device(
            serial_number=request.serial_number,
            user_id=request.user_id
        )
        return {
            "device": device,
            "message": "设备绑定成功"
        }
    except DeviceAlreadyBoundException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": e.code, "message": e.message, "details": e.details}
        )
