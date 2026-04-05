"""Tests for MQTT subscription service"""
import pytest
from datetime import datetime, timezone
from app.services.mqtt_subscription_service import (
    parse_timestamp,
    parse_telemetry_array,
    TELEMETRY_ARRAY_PREFIX_MAP,
    STATUS_FIELD_MAP,
)


def test_parse_timestamp_utc():
    """Test timestamp parsing with UTC Z suffix"""
    ts = parse_timestamp("2026-04-01T12:00:00Z")
    assert ts is not None
    assert ts.tzinfo is not None


def test_parse_timestamp_with_offset():
    """Test timestamp parsing with timezone offset"""
    ts = parse_timestamp("2026-04-01T12:00:00+00:00")
    assert ts is not None
    assert ts.tzinfo is not None


def test_parse_timestamp_invalid():
    """Test invalid timestamp falls back to current UTC"""
    ts = parse_timestamp("invalid-timestamp")
    assert ts is not None
    assert ts.tzinfo is not None


def test_parse_telemetry_array_cell_voltages():
    """Test telemetry array parsing for cell voltages"""
    telemetry_data = {
        "01117001": 3500,  # Cell 1 voltage
        "01117002": 3510,  # Cell 2 voltage
        "01117003": 3490,  # Cell 3 voltage
        "other_field": 42,
    }

    result = parse_telemetry_array(telemetry_data)

    assert "cell_voltages" in result
    assert len(result["cell_voltages"]) == 3
    assert result["cell_voltages"][0] == 3500
    assert result["cell_voltages"][1] == 3510
    assert result["cell_voltages"][2] == 3490


def test_parse_telemetry_array_cell_socs():
    """Test telemetry array parsing for cell SOCs"""
    telemetry_data = {
        "01129001": 950,  # Cell 1 SOC (95.0%)
        "01129002": 940,  # Cell 2 SOC (94.0%)
        "01129003": 960,  # Cell 3 SOC (96.0%)
    }

    result = parse_telemetry_array(telemetry_data)

    assert "cell_socs" in result
    assert len(result["cell_socs"]) == 3
    assert result["cell_socs"][0] == 950
    assert result["cell_socs"][1] == 940


def test_parse_telemetry_array_cell_temperatures():
    """Test telemetry array parsing for cell temperatures"""
    telemetry_data = {
        "01119001": 250,  # Cell 1 temp (25.0°C)
        "01119002": 260,  # Cell 2 temp (26.0°C)
    }

    result = parse_telemetry_array(telemetry_data)

    assert "cell_temperatures" in result
    assert len(result["cell_temperatures"]) == 2
    assert result["cell_temperatures"][0] == 250


def test_parse_telemetry_array_mixed():
    """Test parsing multiple array types together"""
    telemetry_data = {
        "01117001": 3500,  # Cell voltage 1
        "01117002": 3510,  # Cell voltage 2
        "01129001": 950,   # Cell SOC 1
        "01129002": 940,   # Cell SOC 2
        "01119001": 250,   # Cell temp 1
        "voltage": 48.5,   # Non-array field
    }

    result = parse_telemetry_array(telemetry_data)

    assert "cell_voltages" in result
    assert "cell_socs" in result
    assert "cell_temperatures" in result
    assert "voltage" in result  # Non-array field preserved


def test_telemetry_array_prefix_map():
    """Test telemetry array prefix map configuration"""
    assert "011170" in TELEMETRY_ARRAY_PREFIX_MAP
    assert TELEMETRY_ARRAY_PREFIX_MAP["011170"] == "cell_voltages"
    assert "011290" in TELEMETRY_ARRAY_PREFIX_MAP
    assert TELEMETRY_ARRAY_PREFIX_MAP["011290"] == "cell_socs"
    assert "011190" in TELEMETRY_ARRAY_PREFIX_MAP
    assert TELEMETRY_ARRAY_PREFIX_MAP["011190"] == "cell_temperatures"


def test_status_field_map():
    """Test status field map configuration"""
    assert "TS001" in STATUS_FIELD_MAP
    assert STATUS_FIELD_MAP["TS001"] == "operation_status"
    assert "TS002" in STATUS_FIELD_MAP
    assert STATUS_FIELD_MAP["TS002"] == "charge_discharge_status"
