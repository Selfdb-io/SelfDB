/**
 * Mock API Service
 * Provides mock implementations of API services for testing
 */
import { vi } from 'vitest';
import type { AxiosInstance } from 'axios';

/**
 * Creates a mock axios instance for testing
 */
export const createMockAxios = (): AxiosInstance => {
  return {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    request: vi.fn(),
    interceptors: {
      request: {
        use: vi.fn(),
        eject: vi.fn(),
        clear: vi.fn(),
      },
      response: {
        use: vi.fn(),
        eject: vi.fn(),
        clear: vi.fn(),
      },
    },
  } as any;
};

/**
 * Mock successful API response
 */
export const mockApiSuccess = <T,>(data: T) => ({
  data,
  status: 200,
  statusText: 'OK',
  headers: {},
  config: {} as any,
});

/**
 * Mock API error response
 */
export const mockApiError = (message: string, status: number = 400) => ({
  response: {
    data: { message },
    status,
    statusText: 'Error',
    headers: {},
    config: {} as any,
  },
  message,
  name: 'AxiosError',
  config: {} as any,
  isAxiosError: true,
  toJSON: () => ({}),
});

/**
 * Mock user data for testing
 */
export const mockUser = {
  id: '1',
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  role: 'admin',
  is_active: true,
  created_at: '2025-01-01T00:00:00Z',
};

/**
 * Mock auth token
 */
export const mockToken = 'mock-jwt-token-12345';

/**
 * Setup localStorage mock with auth data
 */
export const setupAuthStorage = () => {
  localStorage.setItem('token', mockToken);
  localStorage.setItem('user', JSON.stringify(mockUser));
};

/**
 * Clear auth storage
 */
export const clearAuthStorage = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
};
