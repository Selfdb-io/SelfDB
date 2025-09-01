import axios, { AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios';

// Use relative path for API - Nginx will proxy to the backend container
const API_BASE_URL = '/api/v1';
const ANON_KEY = import.meta.env.VITE_ANON_KEY || '';

// Create an axios instance with base URL
const api = axios.create({
  baseURL: API_BASE_URL,
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

// Add a request interceptor to include the auth token and anon key in requests
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Always attach anon key
    if (config.headers && ANON_KEY) {
      config.headers['apikey'] = ANON_KEY;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to handle common errors
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  async (error: AxiosError) => {
    if (!error.config) {
      return Promise.reject(error);
    }
    
    const originalRequest = error.config;
    
    // Create a type-safe property to track request retries
    const _retry = (originalRequest as any)._retry;
    const url = originalRequest.url || '';
    
    // If error is 401 and it's not a retry or a login/refresh attempt
    if (error.response?.status === 401 && 
        !_retry &&
        !url.includes('/auth/login') && 
        !url.includes('/auth/refresh')) {
      
      if (isRefreshing) {
        // If refresh is already in progress, queue this request to retry later
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(token => {
            if (originalRequest.headers) {
              originalRequest.headers['Authorization'] = `Bearer ${token}`;
            }
            return axios(originalRequest);
          })
          .catch(err => {
            return Promise.reject(err);
          });
      }
      
      (originalRequest as any)._retry = true;
      isRefreshing = true;
      
      try {
        // Try to refresh the token
        const refreshTokenStr = localStorage.getItem('refreshToken');
        
        if (!refreshTokenStr) {
          // No refresh token, log out
          localStorage.removeItem('token');
          localStorage.removeItem('refreshToken');
          processQueue(new Error('No refresh token'));
          isRefreshing = false;
          
          // Redirect to login page if not already there
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
          return Promise.reject(error);
        }
        
        // Make the refresh token call
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshTokenStr
        });
        
        // Store the new access token
        const { access_token } = response.data;
        localStorage.setItem('token', access_token);
        
        // Update the Authorization header for the original request
        if (originalRequest.headers) {
          originalRequest.headers['Authorization'] = `Bearer ${access_token}`;
        }
        
        // Process all pending requests
        processQueue(null, access_token);
        isRefreshing = false;
        
        // Retry the original request
        return axios(originalRequest);
      } catch (refreshError) {
        // Failed to refresh token, logout
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        
        // Process all pending requests with error
        processQueue(new Error('Failed to refresh token'));
        isRefreshing = false;
        
        // Redirect to login page if not already there
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

// App constants
export const APP_NAME = 'SelfDB';
export const APP_VERSION = '1.1.0';

// Export the Swagger docs URL for use in the frontend - use relative path
export const SWAGGER_DOCS_URL = '/redoc';

export default api; 