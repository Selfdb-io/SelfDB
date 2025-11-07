import api from './api';

export interface Webhook {
  id: string;
  function_id: string;
  owner_id: string;
  name: string;
  description?: string;
  provider?: string;
  provider_event_type?: string;
  source_url?: string;
  webhook_token: string;
  secret_key?: string;
  path_segment: string;
  is_active: boolean;
  rate_limit_per_minute: number;
  max_queue_size?: number;
  retry_enabled: boolean;
  retry_attempts: number;
  retry_backoff_strategy: string;
  retry_delay_seconds: number;
  retry_max_delay_seconds: number;
  payload_schema?: any;
  expected_headers?: Record<string, string>;
  transform_script?: string;
  is_active_delivery?: boolean;
  last_received_at?: string;
  last_delivery_status?: string;
  successful_delivery_count: number;
  failed_delivery_count: number;
  total_delivery_count: number;
  created_at: string;
  updated_at: string;
}

export interface WebhookListResponse {
  webhooks: Webhook[];
  total: number;
  limit: number;
  offset: number;
}

export interface WebhookDelivery {
  id: string;
  webhook_id: string;
  function_id: string;
  source_ip: string;
  source_user_agent?: string;
  request_headers: Record<string, any>;
  request_body: any;
  request_body_size_bytes: number;
  request_method: string;
  request_url: string;
  signature_header_name?: string;
  signature_provided?: string;
  signature_valid: boolean;
  signature_error?: string;
  payload_valid?: boolean;
  validation_errors?: any;
  transformed_payload?: any;
  transform_error?: string;
  queued_at: string;
  status: string;
  delivery_attempt: number;
  processing_started_at?: string;
  function_execution_id?: string;
  execution_result?: any;
  execution_error?: string;
  error_message?: string;
  execution_time_ms?: number;
  response_status_code?: number;
  response_headers?: Record<string, any>;
  response_body?: any;
  retry_count: number;
  next_retry_at?: string;
  retry_reason?: string;
  processed_by_user_id?: string;
  processed_at?: string;
  created_at: string;
  received_at: string;
  processing_completed_at?: string;
  updated_at: string;
}

export interface WebhookDeliveryListResponse {
  deliveries: WebhookDelivery[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateWebhookRequest {
  name: string;
  function_id: string;
  description?: string;
  provider?: string;
  provider_event_type?: string;
  source_url?: string;
  secret_key: string;
  rate_limit_per_minute?: number;
  retry_attempts?: number;
  retry_backoff_strategy?: 'exponential' | 'linear' | 'fixed';
  retry_delay_seconds?: number;
  retry_max_delay_seconds?: number;
}

export interface UpdateWebhookRequest {
  // Allow updating the same fields available during creation
  name?: string;
  function_id?: string;
  description?: string;
  provider?: string;
  provider_event_type?: string;
  source_url?: string;
  secret_key?: string;
  is_active?: boolean;
  rate_limit_per_minute?: number;
  retry_attempts?: number;
  retry_backoff_strategy?: 'exponential' | 'linear' | 'fixed';
  retry_delay_seconds?: number;
  retry_max_delay_seconds?: number;
}

const normalizeWebhook = (r: any): Webhook => ({
  id: r.id,
  function_id: r.function_id,
  owner_id: r.owner_id,
  name: r.name,
  description: r.description || undefined,
  provider: r.provider || undefined,
  provider_event_type: r.provider_event_type || undefined,
  source_url: r.source_url || undefined,
  webhook_token: r.webhook_token,
  secret_key: r.secret_key || undefined,
  path_segment: r.path_segment,
  is_active: r.is_active,
  rate_limit_per_minute: r.rate_limit_per_minute,
  max_queue_size: r.max_queue_size || undefined,
  retry_enabled: r.retry_enabled !== undefined ? r.retry_enabled : true,
  retry_attempts: r.retry_attempts,
  retry_backoff_strategy: r.retry_backoff_strategy,
  retry_delay_seconds: r.retry_delay_seconds,
  retry_max_delay_seconds: r.retry_max_delay_seconds,
  payload_schema: r.payload_schema || undefined,
  expected_headers: r.expected_headers || undefined,
  transform_script: r.transform_script || undefined,
  is_active_delivery: r.is_active_delivery || undefined,
  last_received_at: r.last_received_at || undefined,
  last_delivery_status: r.last_delivery_status || undefined,
  successful_delivery_count: r.successful_delivery_count,
  failed_delivery_count: r.failed_delivery_count,
  total_delivery_count: r.total_delivery_count,
  created_at: r.created_at,
  updated_at: r.updated_at,
});

const normalizeWebhookDelivery = (r: any): WebhookDelivery => ({
  id: r.id,
  webhook_id: r.webhook_id,
  function_id: r.function_id,
  source_ip: r.source_ip,
  source_user_agent: r.source_user_agent || undefined,
  request_headers: (() => {
    const h = r.request_headers || {};
    if (typeof h === 'string') {
      try { return JSON.parse(h); } catch { return {} }
    }
    return h;
  })(),
  request_body: (() => {
    const b = r.request_body;
    if (typeof b === 'string') {
      try { return JSON.parse(b); } catch { return b }
    }
    return b;
  })(),
  request_body_size_bytes: r.request_body_size_bytes,
  request_method: r.request_method,
  request_url: r.request_url,
  signature_header_name: r.signature_header_name || undefined,
  signature_provided: r.signature_provided || undefined,
  signature_valid: r.signature_valid,
  signature_error: r.signature_error || undefined,
  payload_valid: r.payload_valid || undefined,
  validation_errors: r.validation_errors || undefined,
  transformed_payload: r.transformed_payload || undefined,
  transform_error: r.transform_error || undefined,
  queued_at: r.queued_at,
  status: r.status,
  delivery_attempt: r.delivery_attempt,
  processing_started_at: r.processing_started_at || undefined,
  function_execution_id: r.function_execution_id || undefined,
  execution_result: r.execution_result || undefined,
  execution_error: r.execution_error || undefined,
  error_message: r.error_message || undefined,
  execution_time_ms: r.execution_time_ms || undefined,
  response_status_code: r.response_status_code || undefined,
  response_headers: r.response_headers || undefined,
  response_body: r.response_body || undefined,
  retry_count: r.retry_count,
  next_retry_at: r.next_retry_at || undefined,
  retry_reason: r.retry_reason || undefined,
  processed_by_user_id: r.processed_by_user_id || undefined,
  processed_at: r.processed_at || undefined,
  created_at: r.created_at,
  received_at: r.received_at,
  processing_completed_at: r.processing_completed_at || undefined,
  updated_at: r.updated_at,
});

export const getWebhooks = async (limit: number = 20, offset: number = 0): Promise<WebhookListResponse> => {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset)
  });
  const { data } = await api.get(`/webhooks?${params.toString()}`);
  return {
    webhooks: (data.webhooks || []).map(normalizeWebhook),
    total: data.total || 0,
    limit: data.limit || limit,
    offset: data.offset || offset
  };
};

export const getWebhook = async (id: string): Promise<Webhook> => {
  const { data } = await api.get(`/webhooks/${id}`);
  return normalizeWebhook(data);
};

export const createWebhook = async (payload: CreateWebhookRequest): Promise<Webhook> => {
  const body: any = {
    name: payload.name,
    function_id: payload.function_id,
    secret_key: payload.secret_key,
    rate_limit_per_minute: payload.rate_limit_per_minute || 100,
    retry_attempts: payload.retry_attempts || 3,
    retry_backoff_strategy: payload.retry_backoff_strategy || 'exponential',
    retry_delay_seconds: payload.retry_delay_seconds || 60,
    retry_max_delay_seconds: payload.retry_max_delay_seconds || 3600,
  };

  if (payload.description) body.description = payload.description;
  if (payload.provider) body.provider = payload.provider;
  if (payload.provider_event_type) body.provider_event_type = payload.provider_event_type;
  if (payload.source_url) body.source_url = payload.source_url;

  const { data } = await api.post('/webhooks', body);
  return normalizeWebhook(data);
};

export const updateWebhook = async (id: string, payload: UpdateWebhookRequest): Promise<Webhook> => {
  // Send only provided fields in payload
  const body: any = {};
  if (payload.name !== undefined) body.name = payload.name;
  if (payload.function_id !== undefined) body.function_id = payload.function_id;
  if (payload.description !== undefined) body.description = payload.description;
  if (payload.provider !== undefined) body.provider = payload.provider;
  if (payload.provider_event_type !== undefined) body.provider_event_type = payload.provider_event_type;
  if (payload.source_url !== undefined) body.source_url = payload.source_url;
  if (payload.secret_key !== undefined) body.secret_key = payload.secret_key;
  if (payload.is_active !== undefined) body.is_active = payload.is_active;
  if (payload.rate_limit_per_minute !== undefined) body.rate_limit_per_minute = payload.rate_limit_per_minute;
  if (payload.retry_attempts !== undefined) body.retry_attempts = payload.retry_attempts;
  if (payload.retry_backoff_strategy !== undefined) body.retry_backoff_strategy = payload.retry_backoff_strategy;
  if (payload.retry_delay_seconds !== undefined) body.retry_delay_seconds = payload.retry_delay_seconds;
  if (payload.retry_max_delay_seconds !== undefined) body.retry_max_delay_seconds = payload.retry_max_delay_seconds;

  const { data } = await api.put(`/webhooks/${id}`, body);
  return normalizeWebhook(data);
};

export const deleteWebhook = async (id: string): Promise<void> => {
  await api.delete(`/webhooks/${id}`);
};

export const getWebhookDeliveries = async (
  id: string,
  limit: number = 100,
  offset: number = 0
): Promise<WebhookDeliveryListResponse> => {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset)
  });
  const { data } = await api.get(`/webhooks/${id}/deliveries?${params.toString()}`);
  return {
    deliveries: (data.deliveries || []).map(normalizeWebhookDelivery),
    total: data.total || 0,
    limit: data.limit || limit,
    offset: data.offset || offset
  };
};

export const ingestWebhook = async (functionId: string, payload: any, headers?: Record<string, string>): Promise<any> => {
  const requestConfig: any = {
    method: 'POST',
    url: `/webhooks/ingest/${functionId}`,
    data: payload,
  };

  if (headers) {
    requestConfig.headers = headers;
  }

  const { data } = await api.request(requestConfig);
  return data;
};