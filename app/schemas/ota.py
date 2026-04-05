from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class OTAStatus(str, Enum):
    """OTA upgrade status"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


# Valid state transitions
VALID_TRANSITIONS = {
    OTAStatus.PENDING: [OTAStatus.DOWNLOADING, OTAStatus.FAILED],
    OTAStatus.DOWNLOADING: [OTAStatus.INSTALLING, OTAStatus.FAILED, OTAStatus.TIMEOUT],
    OTAStatus.INSTALLING: [OTAStatus.SUCCESS, OTAStatus.FAILED, OTAStatus.TIMEOUT],
    OTAStatus.TIMEOUT: [OTAStatus.PENDING],  # Retry
    OTAStatus.SUCCESS: [],  # Terminal state
    OTAStatus.FAILED: [],  # Terminal state
}


class OtaUpgrade(BaseModel):
    """OTA upgrade model"""
    id: str
    device_id: str
    device_name: Optional[str] = None
    firmware_version: str
    firmware_url: str
    status: OTAStatus
    progress: int = 0
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class OtaUpgradeListResponse(BaseModel):
    """OTA upgrade list response"""
    upgrades: list[OtaUpgrade]
    total: int
    page: int
    page_size: int


class CreateOtaUpgradeRequest(BaseModel):
    """Request to create OTA upgrade"""
    device_id: str = Field(..., description="设备 ID")
    firmware_version: str = Field(..., description="固件版本")
    firmware_url: str = Field(..., description="固件下载 URL")


class OtaProgressUpdate(BaseModel):
    """OTA progress update from device"""
    status: str = Field(..., description="状态")
    progress: int = Field(0, ge=0, le=100, description="进度百分比")
    message: Optional[str] = None
