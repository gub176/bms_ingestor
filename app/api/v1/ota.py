from fastapi import APIRouter, HTTPException, status, Body, Query
from typing import Optional, List
from loguru import logger
from app.services.ota_service import ota_service
from app.core.exceptions import OtaUpgradeNotFoundException, InvalidTransitionException
from app.schemas.ota import CreateOtaUpgradeRequest, OtaProgressUpdate
from app.services.mqtt_service import mqtt_service
from app.services.device_service import device_service
from app.core.exceptions import DeviceOfflineException

router = APIRouter(prefix="/ota", tags=["ota"])


@router.post("/upgrades")
async def create_ota_upgrade(request: CreateOtaUpgradeRequest):
    """创建 OTA 升级任务"""
    # Check if device is online
    device = await device_service.get_device_by_id(request.device_id)
    if device["device"].get("status") != "online":
        raise DeviceOfflineException(request.device_id)

    # Create upgrade task
    upgrade = await ota_service.create_upgrade(
        device_id=request.device_id,
        firmware_version=request.firmware_version,
        firmware_url=request.firmware_url
    )

    # Send MQTT command to device
    try:
        await mqtt_service.send_ota_command(
            device_id=request.device_id,
            ota_url=request.firmware_url,
            version=request.firmware_version
        )
    except Exception as e:
        logger.error(f"Failed to send OTA command: {e}")
        await ota_service.mark_upgrade_failed(upgrade["id"], f"Failed to send command: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTA command: {str(e)}"
        )

    return {"message": "OTA 升级任务已创建", "upgrade": upgrade}


@router.get("/upgrades")
async def get_ota_upgrades(
    device_id: Optional[str] = Query(None, description="设备 ID"),
    status: Optional[str] = Query(None, description="升级状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取 OTA 升级列表"""
    result = await ota_service.get_upgrades(
        device_id=device_id,
        status=status,
        page=page,
        page_size=page_size
    )
    return result


@router.get("/upgrades/{upgrade_id}/progress")
async def get_ota_progress(upgrade_id: str):
    """获取 OTA 升级进度"""
    try:
        upgrade = await ota_service.get_upgrade_by_id(upgrade_id)
        return {
            "upgrade_id": upgrade_id,
            "status": upgrade["status"],
            "progress": upgrade["progress"],
            "error_message": upgrade.get("error_message")
        }
    except OtaUpgradeNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message, "details": e.details}
        )


@router.post("/upgrades/{upgrade_id}/progress")
async def update_ota_progress(upgrade_id: str, request: OtaProgressUpdate):
    """更新 OTA 升级进度 (MQTT Webhook)"""
    try:
        result = await ota_service.update_progress(
            upgrade_id=upgrade_id,
            status=request.status,
            progress=request.progress,
            message=request.message
        )
        return {"message": "进度已更新", "upgrade": result}
    except (OtaUpgradeNotFoundException, InvalidTransitionException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message, "details": e.details}
        )


@router.post("/upgrades/{upgrade_id}/retry")
async def retry_ota_upgrade(upgrade_id: str):
    """重试失败的 OTA 升级"""
    try:
        result = await ota_service.retry_upgrade(upgrade_id)
        return {"message": "OTA 升级已重试", "upgrade": result}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except OtaUpgradeNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message, "details": e.details}
        )
