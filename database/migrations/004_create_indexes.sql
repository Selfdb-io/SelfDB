-- SelfDB Database Indexes
-- Creates indexes for optimal query performance with Functions & Webhooks system

-- Core table indexes
CREATE INDEX IF NOT EXISTS idx_buckets_owner_id ON buckets(owner_id);
CREATE INDEX IF NOT EXISTS idx_files_bucket_id ON files(bucket_id);
CREATE INDEX IF NOT EXISTS idx_files_owner_id ON files(owner_id);
CREATE INDEX IF NOT EXISTS idx_files_name ON files(name);
CREATE INDEX IF NOT EXISTS idx_files_deleted_at ON files(deleted_at);
CREATE INDEX IF NOT EXISTS idx_functions_owner_id ON functions(owner_id);
CREATE INDEX IF NOT EXISTS idx_tables_owner_id ON tables(owner_id);

-- Functions table indexes
CREATE INDEX IF NOT EXISTS idx_functions_name ON functions(name);
CREATE INDEX IF NOT EXISTS idx_functions_is_active ON functions(is_active);
CREATE INDEX IF NOT EXISTS idx_functions_deployment_status ON functions(deployment_status);
CREATE INDEX IF NOT EXISTS idx_functions_created_at ON functions(created_at DESC);

-- Function executions table indexes
CREATE INDEX IF NOT EXISTS idx_function_executions_function_id ON function_executions(function_id);
CREATE INDEX IF NOT EXISTS idx_function_executions_user_id ON function_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_function_executions_status ON function_executions(status);
CREATE INDEX IF NOT EXISTS idx_function_executions_trigger_type ON function_executions(trigger_type);
CREATE INDEX IF NOT EXISTS idx_function_executions_created_at ON function_executions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_function_executions_webhook_delivery_id ON function_executions(webhook_delivery_id);

-- Webhooks table indexes
CREATE INDEX IF NOT EXISTS idx_webhooks_function_id ON webhooks(function_id);
CREATE INDEX IF NOT EXISTS idx_webhooks_token ON webhooks(webhook_token);
CREATE INDEX IF NOT EXISTS idx_webhooks_provider ON webhooks(provider, provider_event_type);
CREATE INDEX IF NOT EXISTS idx_webhooks_owner_id ON webhooks(owner_id);
CREATE INDEX IF NOT EXISTS idx_webhooks_is_active ON webhooks(is_active);
CREATE INDEX IF NOT EXISTS idx_webhooks_created_at ON webhooks(created_at DESC);

-- Webhook deliveries table indexes
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_webhook_id ON webhook_deliveries(webhook_id);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_function_id ON webhook_deliveries(function_id);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_status ON webhook_deliveries(status);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_created_at ON webhook_deliveries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_source_ip ON webhook_deliveries(source_ip);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_signature_valid ON webhook_deliveries(signature_valid);

-- Function logs table indexes
CREATE INDEX IF NOT EXISTS idx_function_logs_execution_id ON function_logs(execution_id);
CREATE INDEX IF NOT EXISTS idx_function_logs_function_id ON function_logs(function_id);
CREATE INDEX IF NOT EXISTS idx_function_logs_log_level ON function_logs(log_level);
CREATE INDEX IF NOT EXISTS idx_function_logs_timestamp ON function_logs(timestamp DESC);

-- System table indexes
CREATE INDEX IF NOT EXISTS idx_system_states_created_at ON system_states(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_active_executions_function_id ON active_executions(function_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_request_id ON audit_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_function_id ON performance_metrics(function_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_created_at ON performance_metrics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_checkpoints_created_at ON system_checkpoints(created_at DESC);

-- Additional useful indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_buckets_name ON buckets(name);
CREATE INDEX IF NOT EXISTS idx_files_is_latest ON files(is_latest);
CREATE INDEX IF NOT EXISTS idx_files_mime_type ON files(mime_type);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_buckets_created_at ON buckets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_data_records_user_id ON data_records(user_id);
CREATE INDEX IF NOT EXISTS idx_data_records_created_at ON data_records(created_at DESC);
