-- SelfDB Database Schema Initialization
-- Creates all required tables for the SelfDB BaaS platform with Functions & Webhooks support

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core Application Tables

-- 1. Users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(20) NOT NULL DEFAULT 'USER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ
);

-- 2. Buckets table
CREATE TABLE IF NOT EXISTS buckets (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    owner_id VARCHAR(36) NOT NULL REFERENCES users(id),
    public BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. Files table
CREATE TABLE IF NOT EXISTS files (
    id VARCHAR(36) PRIMARY KEY,
    bucket_id VARCHAR(36) NOT NULL REFERENCES buckets(id),
    name VARCHAR(500) NOT NULL,
    owner_id VARCHAR(36) REFERENCES users(id),
    size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    metadata JSONB,
    checksum_md5 VARCHAR(32),
    checksum_sha256 VARCHAR(64),
    version INTEGER NOT NULL DEFAULT 1,
    is_latest BOOLEAN NOT NULL DEFAULT TRUE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 4. Functions table (Enhanced for Event-Driven System)
CREATE TABLE IF NOT EXISTS functions (
    id VARCHAR(36) PRIMARY KEY,
    
    -- Basic Metadata
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    code TEXT NOT NULL,
    runtime VARCHAR(50) NOT NULL DEFAULT 'deno',
    owner_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Function Status & Control
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    deployment_status VARCHAR(20) DEFAULT 'pending',
    deployment_error TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Execution Configuration
    timeout_seconds INTEGER NOT NULL DEFAULT 30,
    memory_limit_mb INTEGER NOT NULL DEFAULT 512,
    max_concurrent INTEGER NOT NULL DEFAULT 10,
    
    -- Environment Variables (Encrypted at rest)
    env_vars JSONB DEFAULT '{}',
    env_vars_updated_at TIMESTAMPTZ,
    
    -- Execution Metrics (Cached aggregate data)
    execution_count INTEGER NOT NULL DEFAULT 0,
    execution_success_count INTEGER NOT NULL DEFAULT 0,
    execution_error_count INTEGER NOT NULL DEFAULT 0,
    last_executed_at TIMESTAMPTZ,
    avg_execution_time_ms INTEGER,
    
    -- Timestamps
    last_deployed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT timeout_range CHECK (timeout_seconds >= 5 AND timeout_seconds <= 300),
    CONSTRAINT memory_range CHECK (memory_limit_mb >= 128 AND memory_limit_mb <= 4096),
    CONSTRAINT max_concurrent_range CHECK (max_concurrent >= 1 AND max_concurrent <= 100)
);

-- 5. Tables table (for custom table management)
CREATE TABLE IF NOT EXISTS tables (
    name VARCHAR(255) PRIMARY KEY,
    schema JSONB NOT NULL,
    public BOOLEAN NOT NULL DEFAULT FALSE,
    owner_id VARCHAR(36) NOT NULL REFERENCES users(id),
    description TEXT,
    metadata JSONB,
    row_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 6. Webhooks table (New - External Integration Configuration)
CREATE TABLE IF NOT EXISTS webhooks (
    id VARCHAR(36) PRIMARY KEY,
    function_id VARCHAR(36) NOT NULL REFERENCES functions(id) ON DELETE CASCADE,
    owner_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Webhook Identity
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- External Integration Details
    provider VARCHAR(50),
    provider_event_type VARCHAR(255),
    source_url VARCHAR(500),
    
    -- Webhook Authentication & Routing
    webhook_token VARCHAR(255) NOT NULL UNIQUE,
    secret_key VARCHAR(255) NOT NULL,
    path_segment VARCHAR(100) GENERATED ALWAYS AS (COALESCE(provider, 'custom') || '_' || webhook_token) STORED,
    
    -- Enable/Disable Control
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Rate Limiting & Reliability
    rate_limit_per_minute INTEGER NOT NULL DEFAULT 100,
    max_queue_size INTEGER DEFAULT 1000,
    
    -- Retry Configuration
    retry_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    retry_attempts INTEGER NOT NULL DEFAULT 3,
    retry_backoff_strategy VARCHAR(50) DEFAULT 'exponential',
    retry_delay_seconds INTEGER NOT NULL DEFAULT 60,
    retry_max_delay_seconds INTEGER NOT NULL DEFAULT 3600,
    
    -- Payload Validation & Transformation
    payload_schema JSONB,
    expected_headers JSONB DEFAULT '{}',
    transform_script TEXT,
    
    -- Monitoring & Metrics
    is_active_delivery BOOLEAN DEFAULT FALSE,
    last_received_at TIMESTAMPTZ,
    last_delivery_status VARCHAR(20),
    successful_delivery_count INTEGER DEFAULT 0,
    failed_delivery_count INTEGER DEFAULT 0,
    total_delivery_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT rate_limit_range CHECK (rate_limit_per_minute >= 1 AND rate_limit_per_minute <= 10000),
    CONSTRAINT retry_attempts_range CHECK (retry_attempts >= 1 AND retry_attempts <= 10),
    CONSTRAINT retry_delay_range CHECK (retry_delay_seconds >= 1 AND retry_delay_seconds <= 3600)
);

-- Audit & Logging Tables

-- 7. Function Executions table (Enhanced)
CREATE TABLE IF NOT EXISTS function_executions (
    id VARCHAR(36) PRIMARY KEY,
    function_id VARCHAR(36) NOT NULL REFERENCES functions(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Trigger & Source Information
    trigger_type VARCHAR(20) NOT NULL,
    trigger_source VARCHAR(255),
    webhook_delivery_id VARCHAR(36),
    
    -- Execution State
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    
    -- Timing
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    -- Resource Usage
    memory_used_mb FLOAT,
    cpu_usage_percent FLOAT,
    
    -- Results & Errors
    result JSONB,
    error_message TEXT,
    error_stack_trace TEXT,
    error_type VARCHAR(100),
    
    -- Environment & Debugging
    env_vars_used TEXT[],
    execution_trace JSONB,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_status CHECK (status IN ('running', 'completed', 'failed', 'timeout'))
);

-- 8. Webhook Deliveries table (New - Complete Audit Trail)
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id VARCHAR(36) PRIMARY KEY,
    webhook_id VARCHAR(36) NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    function_id VARCHAR(36) NOT NULL REFERENCES functions(id) ON DELETE CASCADE,
    
    -- Request Information
    source_ip VARCHAR(45),
    source_user_agent TEXT,
    request_headers JSONB,
    request_body JSONB,
    request_body_size_bytes INTEGER,
    request_method VARCHAR(10) DEFAULT 'POST',
    request_url TEXT,
    
    -- Signature Verification
    signature_header_name VARCHAR(100),
    signature_provided VARCHAR(500),
    signature_valid BOOLEAN,
    signature_error TEXT,
    
    -- Schema Validation
    payload_valid BOOLEAN,
    validation_errors JSONB,
    
    -- Transformation & Processing
    transformed_payload JSONB,
    transform_error TEXT,
    queued_at TIMESTAMPTZ,
    
    -- Execution Status
    status VARCHAR(20) NOT NULL DEFAULT 'received',
    delivery_attempt INTEGER NOT NULL DEFAULT 1,
    processing_started_at TIMESTAMPTZ,
    function_execution_id VARCHAR(36) REFERENCES function_executions(id),
    execution_result JSONB,
    execution_error TEXT,
    error_message TEXT,
    execution_time_ms INTEGER,
    response_status_code INTEGER,
    response_headers JSONB,
    response_body TEXT,
    
    -- Retry Management
    retry_count INTEGER NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMPTZ,
    retry_reason TEXT,
    
    -- Audit Trail
    processed_by_user_id VARCHAR(36),
    processed_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processing_completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_status CHECK (status IN ('received', 'validating', 'queued', 'executing', 'completed', 'failed', 'retry_pending'))
);

-- 9. Function Logs table (New - Raw Log Storage)
CREATE TABLE IF NOT EXISTS function_logs (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(36) NOT NULL REFERENCES function_executions(id) ON DELETE CASCADE,
    function_id VARCHAR(36) NOT NULL REFERENCES functions(id) ON DELETE CASCADE,
    
    -- Log Entry
    log_level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    
    -- Context
    context JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Source
    source VARCHAR(100),
    
    CONSTRAINT valid_log_level CHECK (log_level IN ('debug', 'info', 'warn', 'error'))
);

-- System Management Tables

-- 10. Migrations table
CREATE TABLE IF NOT EXISTS migrations (
    id SERIAL PRIMARY KEY,
    version INTEGER NOT NULL UNIQUE,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. Data Records table (generic JSON storage)
CREATE TABLE IF NOT EXISTS data_records (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System Restart Persistence Tables

-- 12. System States table
CREATE TABLE IF NOT EXISTS system_states (
    id VARCHAR(255) PRIMARY KEY,
    state_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 13. Active Executions table
CREATE TABLE IF NOT EXISTS active_executions (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(255) NOT NULL,
    function_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    execution_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 14. Resource Pool States table
CREATE TABLE IF NOT EXISTS resource_pool_states (
    pool_id VARCHAR(255) PRIMARY KEY,
    resource_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 15. Audit Logs table
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

-- 16. Performance Metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    function_id VARCHAR(255) NOT NULL,
    execution_time_ms INTEGER NOT NULL,
    memory_used_mb FLOAT NOT NULL,
    success BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 17. System Checkpoints table
CREATE TABLE IF NOT EXISTS system_checkpoints (
    id VARCHAR(255) PRIMARY KEY,
    checkpoint_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 18. CORS Origins table
CREATE TABLE IF NOT EXISTS cors_origins (
    id VARCHAR(36) PRIMARY KEY,
    origin VARCHAR(500) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    extra_metadata JSONB DEFAULT '{}',
    created_by VARCHAR(36) NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- REALTIME NOTIFY TRIGGERS
-- ================================

-- Generic notify function for all tables
CREATE OR REPLACE FUNCTION notify_table_change()
RETURNS TRIGGER AS $$
DECLARE
  payload JSON;
BEGIN
  IF (TG_OP = 'DELETE') THEN
    payload = json_build_object(
      'action', TG_OP,
      'table', TG_TABLE_NAME,
      'old_data', row_to_json(OLD),
      'timestamp', NOW()
    );
  ELSE
    payload = json_build_object(
      'action', TG_OP,
      'table', TG_TABLE_NAME,
      'new_data', row_to_json(NEW),
      'old_data', CASE WHEN TG_OP = 'UPDATE' THEN row_to_json(OLD) ELSE NULL END,
      'timestamp', NOW()
    );
  END IF;

  -- Send notification on table-specific channel
  PERFORM pg_notify(TG_TABLE_NAME || '_events', payload::text);
  
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$$ LANGUAGE plpgsql;

-- Attach triggers to core tables
CREATE TRIGGER users_notify 
  AFTER INSERT OR UPDATE OR DELETE ON users
  FOR EACH ROW EXECUTE FUNCTION notify_table_change();

CREATE TRIGGER files_notify 
  AFTER INSERT OR UPDATE OR DELETE ON files
  FOR EACH ROW EXECUTE FUNCTION notify_table_change();

CREATE TRIGGER buckets_notify 
  AFTER INSERT OR UPDATE OR DELETE ON buckets
  FOR EACH ROW EXECUTE FUNCTION notify_table_change();

CREATE TRIGGER functions_notify 
  AFTER INSERT OR UPDATE OR DELETE ON functions
  FOR EACH ROW EXECUTE FUNCTION notify_table_change();

CREATE TRIGGER tables_notify 
  AFTER INSERT OR UPDATE OR DELETE ON tables
  FOR EACH ROW EXECUTE FUNCTION notify_table_change();

CREATE TRIGGER webhooks_notify 
  AFTER INSERT OR UPDATE OR DELETE ON webhooks
  FOR EACH ROW EXECUTE FUNCTION notify_table_change();

CREATE TRIGGER webhook_deliveries_notify 
  AFTER INSERT OR UPDATE OR DELETE ON webhook_deliveries
  FOR EACH ROW EXECUTE FUNCTION notify_table_change();
