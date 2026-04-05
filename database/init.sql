-- BMS Cloud Platform Database Schema
-- Verified against Supabase production database (2026-04-05)
-- Execute this in Supabase SQL Editor only if tables don't exist

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Devices table (PRIMARY KEY: device_id as VARCHAR, not UUID)
CREATE TABLE IF NOT EXISTS devices (
    device_id VARCHAR(255) PRIMARY KEY,
    auth_key VARCHAR(255),
    manufacturer VARCHAR(255),
    hw_version VARCHAR(50),
    fw_version VARCHAR(50),
    battery_packs_count INTEGER,
    cell_count INTEGER,
    temp_sensor_count INTEGER,
    last_online TIMESTAMPTZ,
    last_offline TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'inactive',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes on devices
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_last_online ON devices(last_online);

-- Telemetry table (uses device_id as VARCHAR, no id column)
CREATE TABLE IF NOT EXISTS telemetry (
    device_id VARCHAR(255) REFERENCES devices(device_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ,
    received_at TIMESTAMPTZ,
    cell_voltages DECIMAL[],
    cell_socs INTEGER[],
    cell_temperatures DECIMAL[],
    data JSONB
);

-- Create indexes on telemetry
CREATE INDEX IF NOT EXISTS idx_telemetry_device ON telemetry(device_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry(timestamp);

-- Alerts table (id is SERIAL/INTEGER, device_id is VARCHAR)
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(device_id) ON DELETE CASCADE,
    alert_type VARCHAR(100),
    severity INTEGER,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ
);

-- Create indexes on alerts
CREATE INDEX IF NOT EXISTS idx_alerts_device ON alerts(device_id);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_start_time ON alerts(start_time);

-- Offline events table
CREATE TABLE IF NOT EXISTS offline_events (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(device_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ,
    reason VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on offline_events
CREATE INDEX IF NOT EXISTS idx_offline_device ON offline_events(device_id);

-- OTA upgrades table (minimal schema)
CREATE TABLE IF NOT EXISTS ota_upgrades (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(device_id) ON DELETE CASCADE,
    status VARCHAR(50),
    progress INTEGER DEFAULT 0
);

-- Create indexes on OTA
CREATE INDEX IF NOT EXISTS idx_ota_device ON ota_upgrades(device_id);
CREATE INDEX IF NOT EXISTS idx_ota_status ON ota_upgrades(status);

-- Remote commands table
CREATE TABLE IF NOT EXISTS remote_commands (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES devices(device_id) ON DELETE CASCADE,
    command VARCHAR(100),
    params JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes on remote_commands
CREATE INDEX IF NOT EXISTS idx_remote_device ON remote_commands(device_id);
CREATE INDEX IF NOT EXISTS idx_remote_status ON remote_commands(status);

-- User devices mapping table
CREATE TABLE IF NOT EXISTS user_devices (
    user_id VARCHAR(255) NOT NULL,
    device_id VARCHAR(255) REFERENCES devices(device_id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'owner',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, device_id)
);

-- Create index on user_devices
CREATE INDEX IF NOT EXISTS idx_user_devices_user ON user_devices(user_id);
