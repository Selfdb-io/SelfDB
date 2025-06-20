import api from './api';

export interface Function {
  id: string;
  name: string;
  description?: string;
  code: string;
  trigger_type: string;
  created_at: string;
  updated_at: string;
  status: string;
  version: number;
  is_active?: boolean;
}

export interface EnvVar {
  id: string;
  key: string;
  value: string;
  function_id: string;
}

export interface FunctionVersion {
  id: string;
  function_id: string;
  version: number;
  code: string;
  created_at: string;
  status: string;
}

export const getFunctions = async (): Promise<Function[]> => {
  const { data } = await api.get('/functions');
  return data;
};

export const getFunction = async (id: string): Promise<Function> => {
  const { data } = await api.get(`/functions/${id}`);
  return data;
};

export const createFunction = async (payload: Omit<Function, 'id' | 'created_at' | 'updated_at' | 'version'>): Promise<Function> => {
  const { data } = await api.post('/functions', payload);
  return data;
};

export const updateFunction = async (id: string, payload: Partial<Function>): Promise<Function> => {
  const { data } = await api.put(`/functions/${id}`, payload);
  return data;
};

export const deleteFunction = async (id: string): Promise<boolean> => {
  await api.delete(`/functions/${id}`);
  return true;
};

export const getEnvVars = async (id: string): Promise<EnvVar[]> => {
  const { data } = await api.get(`/functions/${id}/env`);
  return data;
};

export const createEnvVar = async (id: string, payload: Omit<EnvVar, 'id' | 'function_id'>): Promise<EnvVar> => {
  const { data } = await api.post(`/functions/${id}/env`, payload);
  return data;
};

export const deleteEnvVar = async (functionId: string, varId: string): Promise<boolean> => {
  await api.delete(`/functions/${functionId}/env/${varId}`);
  return true;
};

export const getFunctionTemplate = async (triggerType: string): Promise<string> => {
  const { data } = await api.get(`/functions/templates/${triggerType}`);
  return data;
};

export const getFunctionVersions = async (id: string): Promise<FunctionVersion[]> => {
  const { data } = await api.get(`/functions/${id}/versions`);
  return data;
}; 