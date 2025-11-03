import api from '../../../services/api';

// Types aligned with backend Pydantic models
export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login_at?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;  // seconds
  user: User;
}

export interface LoginResponse extends TokenResponse {}

export interface ErrorResponse {
  error: string;
  message: string;
  details?: Record<string, any>;
}

// Login user and get token
export const loginUser = async (email: string, password: string): Promise<LoginResponse> => {
  const response = await api.post('/auth/login', {
    email,
    password
  });
  return response.data;
};

// Register a new user
export const registerUser = async (
  email: string,
  password: string,
  first_name: string,
  last_name: string
): Promise<TokenResponse> => {
  const response = await api.post('/auth/register', {
    email,
    password,
    first_name,
    last_name
  });
  return response.data;
};

// Get current user information
export const getCurrentUser = async (): Promise<User> => {
  const response = await api.get('/auth/me');
  return response.data;
};

// Refresh access token using refresh token
export const refreshToken = async (refreshTokenStr: string): Promise<TokenResponse> => {
  const response = await api.post('/auth/refresh', {
    refresh_token: refreshTokenStr
  });
  return response.data;
};

// Logout user
export const logoutUser = async (
  accessToken?: string,
  refreshToken?: string
): Promise<{ message: string }> => {
  const response = await api.post('/auth/logout', {
    access_token: accessToken,
    refresh_token: refreshToken
  });
  return response.data;
};

// Fetch the configured API key for the current admin user
export const getApiKeyForCurrentUser = async (): Promise<{ api_key: string | null }> => {
  const response = await api.get('/auth/me/api-key');
  return response.data;
};