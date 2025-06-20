import api from '../../../services/api';

// Types for authentication responses
export interface LoginResponse {
  access_token: string;
  token_type: string;
  refresh_token: string;
  is_superuser: boolean;
  email: string;
  user_id: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  full_name?: string;
  created_at: string;
}

// Login user and get token
export const loginUser = async (email: string, password: string): Promise<LoginResponse> => {
  const formData = new FormData();
  formData.append('username', email);
  formData.append('password', password);
  
  const response = await api.post('/auth/login', formData);
  return response.data;
};

// Register a new user
export const registerUser = async (email: string, password: string): Promise<User> => {
  const response = await api.post('/auth/register', {
    email,
    password,
    is_active: true,
    is_superuser: false,
  });
  return response.data;
};

// Get current user information
export const getCurrentUser = async (): Promise<User> => {
  const response = await api.get('/users/me');
  return response.data;
};

// Refresh access token using refresh token
export const refreshToken = async (refreshTokenStr: string): Promise<TokenResponse> => {
  const response = await api.post('/auth/refresh', {
    refresh_token: refreshTokenStr
  });
  return response.data;
}; 