"""Tests for alert detector with bitmap deduplication"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.alert_detector import AlertDetector


@pytest.mark.asyncio
async def test_alert_detector_initialization():
    """Test alert detector initializes with empty cache"""
    detector = AlertDetector()
    count = await detector.get_active_alerts_count()
    assert count == 0


@pytest.mark.asyncio
async def test_alert_detector_marks_active():
    """Test marking alert as active"""
    detector = AlertDetector()
    await detector.mark_active("DEVICE_001", "over_voltage")
    assert await detector.is_active("DEVICE_001", "over_voltage") == True
    assert await detector.get_active_alerts_count() == 1


@pytest.mark.asyncio
async def test_alert_detector_marks_inactive():
    """Test marking alert as inactive"""
    detector = AlertDetector()
    await detector.mark_active("DEVICE_001", "over_voltage")
    await detector.mark_inactive("DEVICE_001", "over_voltage")
    assert await detector.is_active("DEVICE_001", "over_voltage") == False


@pytest.mark.asyncio
async def test_alert_detector_process_triggers_alert():
    """Test processing status data triggers alert on bit change"""
    detector = AlertDetector()

    # Status data with alarm signal 01002001, bit 1 (undervoltage) set
    status_data = {
        "01002001": 2  # Bit 1 set = undervoltage
    }
    timestamp = datetime.utcnow()

    alerts_insert, alerts_update = await detector.process("DEVICE_001", timestamp, status_data)

    assert len(alerts_insert) == 1
    assert alerts_insert[0].alert_type == "undervoltage"
    assert alerts_insert[0].device_id == "DEVICE_001"
    assert alerts_insert[0].severity == 1  # Fault severity


@pytest.mark.asyncio
async def test_alert_detector_deduplicates():
    """Test that same alert is not generated twice"""
    detector = AlertDetector()

    status_data = {"01002001": 2}  # undervoltage
    timestamp = datetime.utcnow()

    # First call - should create alert
    alerts1, _ = await detector.process("DEVICE_001", timestamp, status_data)
    assert len(alerts1) == 1

    # Second call with same status - should NOT create alert
    alerts2, _ = await detector.process("DEVICE_001", timestamp, status_data)
    assert len(alerts2) == 0


@pytest.mark.asyncio
async def test_alert_detector_detects_recovery():
    """Test that alert recovery is detected"""
    detector = AlertDetector()
    timestamp = datetime.utcnow()

    # Set alert active
    status_data_on = {"01002001": 2}
    alerts_insert, _ = await detector.process("DEVICE_001", timestamp, status_data_on)
    assert len(alerts_insert) == 1

    # Clear alert (bit goes to 0)
    status_data_off = {"01002001": 0}
    _, alerts_update = await detector.process("DEVICE_001", timestamp, status_data_off)
    assert len(alerts_update) == 1
    assert alerts_update[0]["alert_type"] == "undervoltage"


@pytest.mark.asyncio
async def test_alert_detector_warning_signal():
    """Test processing warning signal 01003001"""
    detector = AlertDetector()
    timestamp = datetime.utcnow()

    # Bit 0 = cell_voltage_low_warning
    status_data = {"01003001": 1}

    alerts_insert, _ = await detector.process("DEVICE_001", timestamp, status_data)

    assert len(alerts_insert) == 1
    assert alerts_insert[0].alert_type == "cell_voltage_low_warning"
    assert alerts_insert[0].severity == 2  # Warning severity


@pytest.mark.asyncio
async def test_alert_detector_multiple_bits():
    """Test processing multiple alert bits at once"""
    detector = AlertDetector()
    timestamp = datetime.utcnow()

    # Bits 0 and 2 set = short_circuit and overvoltage
    status_data = {"01002001": 5}  # Binary: 101

    alerts_insert, _ = await detector.process("DEVICE_001", timestamp, status_data)

    assert len(alerts_insert) == 2
    alert_types = [a.alert_type for a in alerts_insert]
    assert "short_circuit" in alert_types
    assert "overvoltage" in alert_types
