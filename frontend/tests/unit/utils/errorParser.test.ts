import { describe, it, expect } from 'vitest';
import { parseBackendError, type ParsedError } from '../../../src/utils/errorParser';

describe('parseBackendError', () => {
  describe('Network errors', () => {
    it('should handle connection refused errors', () => {
      const error = { request: {} }; // No response property
      const result = parseBackendError(error);

      expect(result).toEqual({
        message: 'Unable to connect to the server. Please check your internet connection and try again.',
        isNetworkError: true
      });
    });
  });

  describe('401 Unauthorized errors', () => {
    it('should parse missing API key error', () => {
      const error = {
        response: {
          status: 401,
          data: {
            error: {
              code: 'INVALID_API_KEY',
              message: 'API key is missing',
              request_id: 'd7119bd4-5bff-4362-bdcb-3d10207d9def'
            }
          }
        }
      };

      const result = parseBackendError(error);

      expect(result).toEqual({
        message: 'API key is missing or invalid. Please check your configuration.',
        code: 'INVALID_API_KEY'
      });
    });

    it('should parse invalid credentials error', () => {
      const error = {
        response: {
          status: 401,
          data: {
            detail: 'Invalid email or password'
          }
        }
      };

      const result = parseBackendError(error);

      expect(result).toEqual({
        message: 'Invalid email or password'
      });
    });

    it('should handle generic 401 errors', () => {
      const error = {
        response: {
          status: 401,
          data: {}
        }
      };

      const result = parseBackendError(error);

      expect(result).toEqual({
        message: 'Authentication failed. Please check your credentials.'
      });
    });
  });

  describe('422 Validation errors', () => {
    it('should parse missing field validation errors', () => {
      const error = {
        response: {
          status: 422,
          data: {
            detail: [
              {
                type: 'missing',
                loc: ['body', 'email'],
                msg: 'Field required',
                input: { username: 'admin@example.com', password: 'wrongpassword' }
              }
            ]
          }
        }
      };

      const result = parseBackendError(error);

      expect(result).toEqual({
        message: 'email: Field required',
        details: [
          {
            type: 'missing',
            loc: ['body', 'email'],
            msg: 'Field required',
            input: { username: 'admin@example.com', password: 'wrongpassword' }
          }
        ]
      });
    });

    it('should parse multiple validation errors', () => {
      const error = {
        response: {
          status: 422,
          data: {
            detail: [
              {
                type: 'missing',
                loc: ['body', 'email'],
                msg: 'Field required'
              },
              {
                type: 'missing',
                loc: ['body', 'password'],
                msg: 'Field required'
              }
            ]
          }
        }
      };

      const result = parseBackendError(error);

      expect(result).toEqual({
        message: 'email: Field required, password: Field required',
        details: [
          {
            type: 'missing',
            loc: ['body', 'email'],
            msg: 'Field required'
          },
          {
            type: 'missing',
            loc: ['body', 'password'],
            msg: 'Field required'
          }
        ]
      });
    });
  });

  describe('Other HTTP status codes', () => {
    it('should handle 400 Bad Request', () => {
      const error = {
        response: {
          status: 400,
          data: { detail: 'Bad request message' }
        }
      };

      const result = parseBackendError(error);

      expect(result).toEqual({
        message: 'Bad request message'
      });
    });

    it('should handle 403 Forbidden', () => {
      const error = {
        response: {
          status: 403,
          data: { detail: 'Access denied' }
        }
      };

      const result = parseBackendError(error);

      expect(result).toEqual({
        message: 'Access denied'
      });
    });

    it('should handle 404 Not Found', () => {
      const error = {
        response: {
          status: 404,
          data: { detail: 'Resource not found' }
        }
      };

      const result = parseBackendError(error);

      expect(result).toEqual({
        message: 'Resource not found'
      });
    });

    it('should handle 429 Too Many Requests', () => {
      const error = {
        response: {
          status: 429,
          data: {}
        }
      };

      const result = parseBackendError(error);

      expect(result).toEqual({
        message: 'Too many requests. Please wait a moment and try again.'
      });
    });

    it('should handle 500 Server Error', () => {
      const error = {
        response: {
          status: 500,
          data: {}
        }
      };

      const result = parseBackendError(error);

      expect(result).toEqual({
        message: 'Server error. Please try again later.'
      });
    });
  });

  describe('Fallback error handling', () => {
    it('should handle unknown error format', () => {
      const error = {
        response: {
          status: 418,
          data: { custom: 'error' }
        }
      };

      const result = parseBackendError(error);

      expect(result).toEqual({
        message: 'An unexpected error occurred.'
      });
    });

    it('should handle error with message field', () => {
      const error = {
        response: {
          status: 418,
          data: { message: 'Custom error message' }
        }
      };

      const result = parseBackendError(error);

      expect(result).toEqual({
        message: 'Custom error message'
      });
    });
  });
});