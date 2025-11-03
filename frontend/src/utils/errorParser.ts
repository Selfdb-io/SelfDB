/**
 * Utility functions for parsing backend error responses
 */

export interface BackendError {
  code?: string;
  message?: string;
  request_id?: string;
}

export interface ValidationError {
  type: string;
  loc: string[];
  msg: string;
  input?: any;
}

export interface ParsedError {
  message: string;
  code?: string;
  details?: ValidationError[];
  isNetworkError?: boolean;
}

/**
 * Parse backend error responses into user-friendly messages
 */
export const parseBackendError = (error: any): ParsedError => {
  // Handle network errors (connection refused, timeout, etc.)
  if (!error.response) {
    return {
      message: 'Unable to connect to the server. Please check your internet connection and try again.',
      isNetworkError: true
    };
  }

  const { status, data } = error.response;

  // Handle different error response formats
  switch (status) {
    case 400:
      return parse400Error(data);
    case 401:
      return parse401Error(data);
    case 403:
      return parse403Error(data);
    case 404:
      return parse404Error(data);
    case 422:
      return parse422Error(data);
    case 429:
      return { message: 'Too many requests. Please wait a moment and try again.' };
    case 500:
      return { message: 'Server error. Please try again later.' };
    default:
      return { message: data?.message || data?.detail || 'An unexpected error occurred.' };
  }
};

/**
 * Parse 400 Bad Request errors
 */
const parse400Error = (data: any): ParsedError => {
  if (data?.error?.message) {
    return {
      message: data.error.message,
      code: data.error.code
    };
  }
  return { message: data?.detail || 'Bad request. Please check your input.' };
};

/**
 * Parse 401 Unauthorized errors
 */
const parse401Error = (data: any): ParsedError => {
  // Handle structured error format
  if (data?.error?.code === 'INVALID_API_KEY') {
    return {
      message: 'API key is missing or invalid. Please check your configuration.',
      code: 'INVALID_API_KEY'
    };
  }

  // Handle simple detail format
  if (data?.detail) {
    return { message: data.detail };
  }

  return { message: 'Authentication failed. Please check your credentials.' };
};

/**
 * Parse 403 Forbidden errors
 */
const parse403Error = (data: any): ParsedError => {
  if (data?.detail) {
    return { message: data.detail };
  }
  return { message: 'Access denied. You do not have permission to perform this action.' };
};

/**
 * Parse 404 Not Found errors
 */
const parse404Error = (data: any): ParsedError => {
  if (data?.detail) {
    return { message: data.detail };
  }
  return { message: 'The requested resource was not found.' };
};

/**
 * Parse 422 Unprocessable Entity errors (validation errors)
 */
const parse422Error = (data: any): ParsedError => {
  if (data?.detail && Array.isArray(data.detail)) {
    const validationErrors = data.detail as ValidationError[];
    const messages = validationErrors.map(err => {
      const field = err.loc[err.loc.length - 1];
      return `${field}: ${err.msg}`;
    });

    return {
      message: messages.join(', '),
      details: validationErrors
    };
  }

  if (data?.detail) {
    return { message: data.detail };
  }

  return { message: 'Validation failed. Please check your input.' };
};