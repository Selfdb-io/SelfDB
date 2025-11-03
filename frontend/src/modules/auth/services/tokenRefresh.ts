import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';
const API_KEY = import.meta.env.VITE_API_KEY || '';

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export async function refreshToken(refreshTokenStr: string): Promise<TokenResponse> {
  const client = axios.create({ baseURL: API_BASE_URL });
  const headers: Record<string, string> = {};
  if (API_KEY) headers['X-API-Key'] = API_KEY;
  const res = await client.post('/auth/refresh', { refresh_token: refreshTokenStr }, { headers });
  return res.data as TokenResponse;
}
