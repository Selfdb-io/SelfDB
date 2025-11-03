import axios, { AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { refreshToken as refreshTokenApi } from '../modules/auth/services/tokenRefresh';

// Use Vite environment variables for API URL and API key
export const getApiBaseUrl = (): string => import.meta.env.VITE_API_URL || '/api/v1';
const API_KEY = import.meta.env.VITE_API_KEY || '';

// Debug: Log the API configuration in development
if (import.meta.env.VITE_DEBUG === 'true') {
  console.log('🔧 API Configuration:', {
    baseURL: getApiBaseUrl(),
    apiKey: API_KEY ? '***configured***' : 'missing',
    env: import.meta.env.VITE_ENV,
  });
}

// Create an axios instance with base URL from environment
const api = axios.create({
  baseURL: getApiBaseUrl(),
});

// Define the queue item interface
interface QueueItem {
  resolve: (value: any) => void;
  reject: (reason?: any) => void;
}

// Track if token refresh is already in progress
let isRefreshing = false;
// Store pending requests that should be retried after token refresh
let failedQueue: QueueItem[] = [];

// Process the failed queue - retry or reject requests
const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  
  failedQueue = [];
};

// Add a request interceptor to include the auth token and API key in requests
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Always attach API key
    if (config.headers && API_KEY) {
      config.headers['X-API-Key'] = API_KEY;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling token refresh
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean; _skipAuthRefresh?: boolean };
    
    // Skip refresh logic for /auth/refresh endpoint to prevent infinite loop
    if (originalRequest.url?.includes('/auth/refresh')) {
      return Promise.reject(error);
    }
    
    // If error is 401 Unauthorized and we haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      // If token refresh is already in progress, queue this request
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${token}`;
          }
          return api.request(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }
      
      // Set refreshing flag and attempt to refresh token
      isRefreshing = true;
      
      try {
        const refreshTokenStr = localStorage.getItem('refreshToken');
        if (!refreshTokenStr) {
          throw new Error('No refresh token available');
        }
        
        // Create timeout promise to prevent hanging
        const timeoutPromise = new Promise((_, reject) => {
          setTimeout(() => reject(new Error('Token refresh timeout')), 10000); // 10 second timeout
        });
        
        // Race between refresh and timeout
        const response = await Promise.race([
          refreshTokenApi(refreshTokenStr),
          timeoutPromise
        ]) as { access_token: string; refresh_token: string };
        
        // CRITICAL FIX: Store BOTH access_token AND refresh_token
        localStorage.setItem('token', response.access_token);
        localStorage.setItem('refreshToken', response.refresh_token);
        
        // Update authorization header
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${response.access_token}`;
        }
        
        // Process all queued requests with new token
        processQueue(null, response.access_token);
        
        // Retry original request
        return api.request(originalRequest);
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError);
        
        // Clear all tokens and reject queued requests
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        processQueue(refreshError as Error, null);
        
        // Redirect to login page
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;