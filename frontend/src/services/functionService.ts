import api from './api';

export interface SelfFunction {
  id: string;
  name: string;
  description?: string;
  code: string;
  runtime: string;
  owner_id: string;
  is_active: boolean;
  deployment_status: string;
  deployment_error?: string;
  version: number;
  timeout_seconds: number;
  memory_limit_mb: number;
  max_concurrent: number;
  env_vars: Record<string, string>; // Object with env var key-value pairs
  env_vars_updated_at?: string;
  execution_count: number;
  execution_success_count: number;
  execution_error_count: number;
  last_executed_at?: string;
  avg_execution_time_ms?: number;
  last_deployed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface FunctionListResponse {
  functions: SelfFunction[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateFunctionRequest {
  name: string;
  description?: string;
  code: string;
  runtime?: string;
  timeout_seconds?: number;
  memory_limit_mb?: number;
  max_concurrent?: number;
  env_vars?: Record<string, string>;
}

export interface UpdateFunctionRequest {
  description?: string;
  code?: string;
  timeout_seconds?: number;
  memory_limit_mb?: number;
  max_concurrent?: number;
}

export interface SetFunctionStateRequest {
  is_active: boolean;
}

export interface SetEnvVarsRequest {
  env_vars: Record<string, string>;
}

export interface FunctionExecution {
  id: string;
  function_id: string;
  user_id: string;
  trigger_type: string;
  trigger_source?: string;
  webhook_delivery_id?: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  memory_used_mb?: number;
  cpu_usage_percent?: number;
  result?: string;
  error_message?: string;
  error_type?: string;
  created_at?: string;
  updated_at?: string;
}

export interface FunctionExecutionsResponse {
  executions: FunctionExecution[];
  total: number;
  limit: number;
  offset: number;
}

const normalizeFn = (r: any): SelfFunction => ({
  id: r.id,
  name: r.name,
  description: r.description || '',
  code: r.code || '',
  runtime: r.runtime || 'deno',
  owner_id: r.owner_id,
  is_active: r.is_active,
  deployment_status: r.deployment_status || 'pending',
  deployment_error: r.deployment_error || undefined,
  version: r.version || 1,
  timeout_seconds: r.timeout_seconds || 30,
  memory_limit_mb: r.memory_limit_mb || 512,
  max_concurrent: r.max_concurrent || 10,
  env_vars: r.env_vars || {},
  env_vars_updated_at: r.env_vars_updated_at || undefined,
  execution_count: r.execution_count || 0,
  execution_success_count: r.execution_success_count || 0,
  execution_error_count: r.execution_error_count || 0,
  last_executed_at: r.last_executed_at || undefined,
  avg_execution_time_ms: r.avg_execution_time_ms || undefined,
  last_deployed_at: r.last_deployed_at || undefined,
  created_at: r.created_at,
  updated_at: r.updated_at,
});

export const getFunctions = async (limit: number = 20, offset: number = 0): Promise<FunctionListResponse> => {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset)
  });
  const { data } = await api.get(`/functions?${params.toString()}`);
  return {
    functions: (data.functions || []).map(normalizeFn),
    total: data.total || 0,
    limit: data.limit || limit,
    offset: data.offset || offset
  };
};

export const getFunction = async (id: string): Promise<SelfFunction> => {
  const { data } = await api.get(`/functions/${id}`);
  return normalizeFn(data);
};

export const createFunction = async (payload: CreateFunctionRequest): Promise<SelfFunction> => {
  const body: any = {
    name: payload.name,
    description: payload.description || '',
    code: payload.code,
    runtime: payload.runtime || 'deno',
    timeout_seconds: payload.timeout_seconds || 30,
    memory_limit_mb: payload.memory_limit_mb || 512,
    max_concurrent: payload.max_concurrent || 10,
  };
  if (payload.env_vars) {
    body.env_vars = payload.env_vars;
  }
  const { data } = await api.post('/functions', body);
  return normalizeFn(data);
};

export const updateFunction = async (id: string, payload: UpdateFunctionRequest): Promise<SelfFunction> => {
  const { data } = await api.put(`/functions/${id}`, payload);
  return normalizeFn(data);
};

export const setFunctionState = async (id: string, isActive: boolean): Promise<SelfFunction> => {
  const { data } = await api.patch(`/functions/${id}/state`, { is_active: isActive });
  return normalizeFn(data);
};

export const deleteFunction = async (id: string): Promise<void> => {
  await api.delete(`/functions/${id}`);
};

export const setEnvVars = async (id: string, envVars: Record<string, string>): Promise<SelfFunction> => {
  const { data } = await api.post(`/functions/${id}/env-vars`, { env_vars: envVars });
  return normalizeFn(data);
};

export const getEnvVarNames = async (id: string): Promise<string[]> => {
  const { data } = await api.get(`/functions/${id}/env-vars`);
  return Object.keys(data.env_vars || {});
};

export const getFunctionLogs = async (id: string, limit: number = 100, offset: number = 0): Promise<any> => {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset)
  });
  const { data } = await api.get(`/functions/${id}/logs?${params.toString()}`);
  return data;
};

export const getFunctionMetrics = async (id: string): Promise<any> => {
  const { data } = await api.get(`/functions/${id}/metrics`);
  return data;
};

export const getFunctionExecutions = async (
  functionId: string,
  limit: number = 100,
  offset: number = 0,
  status?: string,
  triggerType?: string
): Promise<FunctionExecutionsResponse> => {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset)
  });
  
  if (status) params.append('status', status);
  if (triggerType) params.append('trigger_type', triggerType);
  
  const { data } = await api.get(`/functions/${functionId}/executions?${params.toString()}`);
  return data;
};

// Legacy compatibility - these will be removed once components are updated
export const executeFunction = async (_id: string, _input: any): Promise<any> => {
  // This endpoint doesn't exist in the new API - functions are executed via webhooks or triggers
  throw new Error('Direct function execution not supported in new API');
};

export const getExecutions = async (_id: string): Promise<any> => {
  // This endpoint doesn't exist in the new API
  throw new Error('Execution history not available in new API');
};

export const getExecutionDetails = async (_id: string, _execId: string): Promise<any> => {
  // This endpoint doesn't exist in the new API
  throw new Error('Execution details not available in new API');
};

export const getExecutionLogs = async (_id: string, _execId: string): Promise<any> => {
  // This endpoint doesn't exist in the new API
  throw new Error('Execution logs not available in new API');
};

// Legacy webhook functions - these will be moved to webhookService
export const enableWebhook = async (_id: string, _cfg: any = {}): Promise<any> => {
  throw new Error('Webhooks are now managed separately - use webhookService');
};

export const disableWebhook = async (_id: string): Promise<any> => {
  throw new Error('Webhooks are now managed separately - use webhookService');
};

export const getWebhookConfig = async (_id: string): Promise<any> => {
  throw new Error('Webhooks are now managed separately - use webhookService');
};

export const updateWebhookConfig = async (_id: string, _cfg: any): Promise<any> => {
  throw new Error('Webhooks are now managed separately - use webhookService');
};

export const getWebhookLogs = async (_id: string, _opts?: { limit?: number; offset?: number }): Promise<any> => {
  throw new Error('Webhooks are now managed separately - use webhookService');
};