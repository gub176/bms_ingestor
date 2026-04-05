from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime


class Device(BaseModel):
    """Device model"""
    model_config = ConfigDict(from_attributes=True)

    device_id: Optional[str] = None
    id: Optional[str] = None  # For backward compatibility
    name: Optional[str] = None
    serial_number: Optional[str] = None
    user_id: Optional[str] = None
    status: Optional[str] = "inactive"
    last_seen: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DeviceListResponse(BaseModel):
    """Device list response"""
    devices: list[Device]
    total: int
    page: int
    page_size: int


class DeviceDetailResponse(BaseModel):
    """Device detail response with telemetry and alerts"""
    device: Device
    telemetry: Optional[dict] = None
    alert_stats: Optional[dict] = None


class BindDeviceRequest(BaseModel):
    """Request to bind a device"""
    serial_number: str = Field(..., description="设备序列号")
    user_id: str = Field(..., description="用户 ID")


class BindDeviceResponse(BaseModel):
    """Response after binding a device"""
    device: Device
    message: str = "设备绑定成功"
