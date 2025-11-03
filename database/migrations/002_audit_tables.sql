-- SelfDB Webhooks & Executions Migration
-- Creates webhooks, webhook deliveries, and enhanced function execution tables

-- Function Executions table (Enhanced)
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

-- Webhooks table (New - External Integration Configuration)
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

-- Webhook Deliveries table (New - Complete Audit Trail)
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

-- Function Logs table (New - Raw Log Storage)
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
