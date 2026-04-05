from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class TelemetryData(BaseModel):
    """Telemetry data from device"""
    device_id: str = Field(..., description="设备 ID")
    voltage: Optional[float] = None
    current: Optional[float] = None
    temperature: Optional[float] = None
    soc: Optional[int] = Field(None, ge=0, le=100, description="State of Charge (%)")
    soe: Optional[int] = Field(None, ge=0, le=100, description="State of Energy (%)")
    timestamp: Optional[str] = None


class RemoteCommand(BaseModel):
    """Remote command request"""
    device_id: str = Field(..., description="设备 ID")
    command: str = Field(..., description="命令类型")
    params: Optional[Dict[str, Any]] = Field(None, description="命令参数")


class CommandResponse(BaseModel):
    """Command execution response"""
    command_id: str
    device_id: str
    command: str
    status: str
    result: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class CommandStatusResponse(BaseModel):
    """Command status response"""
    command_id: str
    device_id: str
    command: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
