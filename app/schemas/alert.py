from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime


class Alert(BaseModel):
    """Alert model"""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    device_id: str
    alert_type: str
    severity: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class AlertListResponse(BaseModel):
    """Alert list response"""
    alerts: list[Alert]
    total: int
    page: int
    page_size: int


class AlertStatsResponse(BaseModel):
    """Alert statistics response"""
    total: int
    by_severity: dict[str, int]
    by_device: dict[str, int]
    by_type: dict[str, int]
