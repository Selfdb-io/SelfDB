import { getApiBaseUrl } from '../services/api';

/**
 * Converts HTTP(S) API URL to WebSocket URL
 * @param apiUrl - The base API URL (e.g., http://localhost:8000/api/v1)
 * @returns WebSocket URL (e.g., ws://localhost:8000/api/v1/realtime/ws)
 *
 * @example
 * getWebSocketUrl('http://localhost:8000/api/v1') // => 'ws://localhost:8000/api/v1/realtime/ws'
 * getWebSocketUrl('https://api.example.com/api/v1') // => 'wss://api.example.com/api/v1/realtime/ws'
 */
export const getWebSocketUrl = (apiUrl: string): string => {
  // Replace http:// with ws:// or https:// with wss://
  const wsProtocol = apiUrl.replace(/^http/, 'ws');

  // Add /realtime/ws to the API base URL
  const wsUrl = `${wsProtocol}${apiUrl}/realtime/ws`;

  return wsUrl;
};

/**
 * Get the WebSocket URL from environment configuration
 * @returns Configured WebSocket URL
 */
export const getConfiguredWebSocketUrl = (): string => {
  const apiUrl = getApiBaseUrl();
  return getWebSocketUrl(apiUrl);
};
