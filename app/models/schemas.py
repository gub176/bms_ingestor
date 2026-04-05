"""Data models for MQTT ingestion"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class QueueItem:
    """Queue item for batch processing"""
    op_type: str
    data: Any


@dataclass
class TelemetryRecord:
    """Telemetry record"""
    device_id: str
    timestamp: str
    received_at: str
    data: Dict[str, Any] = field(default_factory=dict)
    cell_voltages: List[float] = field(default_factory=list)
    cell_socs: List[float] = field(default_factory=list)
    cell_temperatures: List[float] = field(default_factory=list)


@dataclass
class StatusRecord:
    """Status record"""
    device_id: str
    timestamp: str
    received_at: str
    operation_status: Optional[int] = None
    charge_discharge_status: Optional[int] = None
    grid_connection_status: Optional[int] = None
    main_contactor_status: Optional[int] = None
    emergency_stop_status: Optional[int] = None
    battery_balancing_status: Optional[int] = None


@dataclass
class Alert:
    """Alert record"""
    device_id: str
    alert_type: str
    severity: int
    start_time: str
    end_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


@dataclass
class OfflineEvent:
    """Device offline event"""
    device_id: str
    timestamp: str
    reason: str
    created_at: str
