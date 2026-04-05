-- BMS Cloud Platform Database Schema
-- Execute this script in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Devices table
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    serial_number VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255),
    name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'inactive',
    last_seen TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on serial_number for faster lookups
CREATE INDEX IF NOT EXISTS idx_devices_serial ON devices(serial_number);
CREATE INDEX IF NOT EXISTS idx_devices_user ON devices(user_id);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);

-- Telemetry table
CREATE TABLE IF NOT EXISTS telemetry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    voltage DECIMAL,
    current DECIMAL,
    temperature DECIMAL,
    soc INTEGER,
    soe INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on device_id and timestamp for faster queries
CREATE INDEX IF NOT EXISTS idx_telemetry_device ON telemetry(device_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry(timestamp);

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    level VARCHAR(50),
    type VARCHAR(100),
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- Create index on device_id and status
CREATE INDEX IF NOT EXISTS idx_alerts_device ON alerts(device_id);
CREATE INDEX IF NOT EXISTS idx_alerts_level ON alerts(level);
CREATE INDEX IF NOT EXISTS idx_alerts_is_read ON alerts(is_read);

-- Alert thresholds table
CREATE TABLE IF NOT EXISTS alert_thresholds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID UNIQUE REFERENCES devices(id) ON DELETE CASCADE,
    over_voltage DECIMAL,
    under_voltage DECIMAL,
    over_current DECIMAL,
    over_temperature DECIMAL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- OTA upgrades table
CREATE TABLE IF NOT EXISTS ota_upgrades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    firmware_version VARCHAR(100),
    firmware_url TEXT,
    status VARCHAR(50),
    progress INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on device_id and status
CREATE INDEX IF NOT EXISTS idx_ota_device ON ota_upgrades(device_id);
CREATE INDEX IF NOT EXISTS idx_ota_status ON ota_upgrades(status);

-- Remote command/adjustment table
CREATE TABLE IF NOT EXISTS remote_adjust (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    command VARCHAR(100),
    params JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on device_id and status
CREATE INDEX IF NOT EXISTS idx_remote_device ON remote_adjust(device_id);
CREATE INDEX IF NOT EXISTS idx_remote_status ON remote_adjust(status);

-- Offline events table
CREATE TABLE IF NOT EXISTS offline_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    offline_at TIMESTAMPTZ DEFAULT NOW(),
    recovered_at TIMESTAMPTZ
);

-- Create index on device_id
CREATE INDEX IF NOT EXISTS idx_offline_device ON offline_events(device_id);

-- Threshold templates table
CREATE TABLE IF NOT EXISTS threshold_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    over_voltage DECIMAL,
    under_voltage DECIMAL,
    over_current DECIMAL,
    over_temperature DECIMAL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User devices mapping table (for many-to-many relationships)
CREATE TABLE IF NOT EXISTS user_devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, device_id)
);

-- Create index on user_id
CREATE INDEX IF NOT EXISTS idx_user_devices_user ON user_devices(user_id);

-- Insert default threshold template
INSERT INTO threshold_templates (name, description, over_voltage, under_voltage, over_current, over_temperature, is_default)
VALUES (
    'Default Template',
    'Default threshold settings for BMS devices',
    54.0,  -- over_voltage (V)
    42.0,  -- under_voltage (V)
    20.0,  -- over_current (A)
    60.0   -- over_temperature (C)
) ON CONFLICT DO NOTHING;
