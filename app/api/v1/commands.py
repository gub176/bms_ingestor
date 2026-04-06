from fastapi import APIRouter, HTTPException, status, Body, Query
from typing import Optional, List
from app.services.mqtt_service import mqtt_service
from app.services.command_service import command_service
from app.services.device_service import device_service
from app.services.alert_judgment import alert_judgment_service
from app.db.supabase import supabase
from app.core.exceptions import DeviceNotFoundException, CommandNotFoundException, DeviceOfflineException
from app.schemas.command import RemoteCommand, TelemetryData
from loguru import logger
from datetime import datetime

router = APIRouter(tags=["mqtt"])


@router.post("/mqtt/telemetry")
async def receive_telemetry(data: TelemetryData):
    """Receive telemetry data from device (MQTT Webhook)"""
    logger.info(f"Telemetry received from device {data.device_id}: {data.dict()}")

    # Insert telemetry data
    telemetry_data = data.dict(exclude_unset=True)
    telemetry_data["timestamp"] = data.timestamp or datetime.utcnow().isoformat()

    supabase.table("telemetry").upsert(telemetry_data, on_conflict="device_id,timestamp").execute()

    # Update device last_seen
    supabase.table("devices") \
        .update({
            "last_seen": telemetry_data["timestamp"],
            "status": "online",
            "updated_at": datetime.utcnow().isoformat()
        }) \
        .eq("id", data.device_id) \
        .execute()

    # Trigger alert judgment asynchronously
    try:
        await alert_judgment_service.check_telemetry_and_alert(data.device_id, data.dict())
    except Exception as e:
        logger.error(f"Alert judgment failed: {e}")

    return {"message": "Telemetry data received"}


@router.post("/mqtt/ota/progress")
async def receive_ota_progress(
    upgrade_id: str = Body(...),
    status: str = Body(...),
    progress: int = Body(0),
    message: Optional[str] = Body(None)
):
    """Receive OTA progress update from device (MQTT Webhook)"""
    from app.services.ota_service import ota_service
    from app.core.exceptions import OtaUpgradeNotFoundException, InvalidTransitionException

    logger.info(f"OTA progress received for upgrade {upgrade_id}: {status} ({progress}%)")

    try:
        result = await ota_service.update_progress(
            upgrade_id=upgrade_id,
            status=status,
            progress=progress,
            message=message
        )
        return {"message": "OTA progress updated", "upgrade": result}
    except (OtaUpgradeNotFoundException, InvalidTransitionException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message, "details": e.details}
        )


@router.post("/commands", response_model=dict)
async def send_remote_command(request: RemoteCommand):
    """Send remote command to device"""
    # Check if device exists and is online
    try:
        device = await device_service.get_device_by_id(request.device_id)
        if device["device"].get("status") != "online":
            raise DeviceOfflineException(request.device_id)
    except DeviceNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DEVICE_NOT_FOUND", "message": "设备不存在"}
        )

    # Create command record
    command = await command_service.create_command(
        device_id=request.device_id,
        command=request.command,
        params=request.params
    )

    # Send MQTT command
    try:
        await mqtt_service.send_remote_command(
            device_id=request.device_id,
            command=request.command,
            params=request.params
        )
    except Exception as e:
        logger.error(f"Failed to send command: {e}")
        await command_service.update_command_status(command["id"], "failed", error_message=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send command: {str(e)}"
        )

    return {"message": "命令已发送", "command": command}


@router.get("/commands/{command_id}", response_model=dict)
async def get_command_status(command_id: str):
    """Get command execution status"""
    try:
        command = await command_service.get_command_by_id(command_id)
        return command
    except CommandNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message, "details": e.details}
        )


@router.get("/commands")
async def get_commands(
    device_id: Optional[str] = Query(None, description="设备 ID"),
    status: Optional[str] = Query(None, description="执行状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """Get command list"""
    result = await command_service.get_commands(
        device_id=device_id,
        status=status,
        page=page,
        page_size=page_size
    )
    return result
