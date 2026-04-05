from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Threshold(BaseModel):
    """Threshold configuration model"""
    id: Optional[str] = None
    device_id: str
    over_voltage: Optional[float] = None
    under_voltage: Optional[float] = None
    over_current: Optional[float] = None
    over_temperature: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ThresholdTemplate(BaseModel):
    """Threshold template model"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    over_voltage: Optional[float] = None
    under_voltage: Optional[float] = None
    over_current: Optional[float] = None
    over_temperature: Optional[float] = None
    is_default: bool = False
    created_at: Optional[datetime] = None


class ThresholdListResponse(BaseModel):
    """Threshold list response"""
    thresholds: list[Threshold]
    total: int
