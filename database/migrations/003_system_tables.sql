-- SelfDB System Tables Migration
-- Creates system management and persistence tables for SelfDB BaaS platform

-- Migrations table
CREATE TABLE IF NOT EXISTS migrations (
    id SERIAL PRIMARY KEY,
    version INTEGER NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64)
);

-- System States table
CREATE TABLE IF NOT EXISTS system_states (
    id VARCHAR(255) PRIMARY KEY,
    state_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Active Executions table
CREATE TABLE IF NOT EXISTS active_executions (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(255) NOT NULL,
    function_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    execution_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Resource Pool States table
CREATE TABLE IF NOT EXISTS resource_pool_states (
    pool_id VARCHAR(255) PRIMARY KEY,
    resource_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Audit Logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    function_id VARCHAR(255),
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    success BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Performance Metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    function_id VARCHAR(255) NOT NULL,
    execution_time_ms INTEGER NOT NULL,
    memory_used_mb FLOAT NOT NULL,
    success BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- System Checkpoints table
CREATE TABLE IF NOT EXISTS system_checkpoints (
    id VARCHAR(255) PRIMARY KEY,
    checkpoint_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);