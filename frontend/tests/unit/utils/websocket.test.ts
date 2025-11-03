/**
 * WebSocket Utility Tests
 * Tests for dynamic WebSocket URL generation
 */
import { describe, it, expect } from 'vitest';
import { getWebSocketUrl, getConfiguredWebSocketUrl } from '@/utils/websocket';

describe('WebSocket Utility', () => {
  describe('getWebSocketUrl', () => {
    it('should convert http to ws protocol', () => {
      const apiUrl = 'http://localhost:8000/api/v1';
      const wsUrl = getWebSocketUrl(apiUrl);
      
      expect(wsUrl).toBe('ws://localhost:8000/ws');
    });

    it('should convert https to wss protocol', () => {
      const apiUrl = 'https://api.example.com/api/v1';
      const wsUrl = getWebSocketUrl(apiUrl);
      
      expect(wsUrl).toBe('wss://api.example.com/ws');
    });

    it('should replace /api/v1 with /ws', () => {
      const apiUrl = 'http://localhost:8000/api/v1';
      const wsUrl = getWebSocketUrl(apiUrl);
      
      expect(wsUrl).not.toContain('/api/v1');
      expect(wsUrl).toContain('/ws');
    });

    it('should handle URLs without trailing slash', () => {
      const apiUrl = 'http://localhost:8000/api/v1';
      const wsUrl = getWebSocketUrl(apiUrl);
      
      expect(wsUrl).toBe('ws://localhost:8000/ws');
    });

    it('should handle URLs with different ports', () => {
      const apiUrl = 'http://localhost:8010/api/v1';
      const wsUrl = getWebSocketUrl(apiUrl);
      
      expect(wsUrl).toBe('ws://localhost:8010/ws');
    });
  });

  describe('getConfiguredWebSocketUrl', () => {
    it('should return WebSocket URL from environment configuration', () => {
      const wsUrl = getConfiguredWebSocketUrl();
      
      // Should be valid WebSocket URL
      expect(wsUrl).toMatch(/^wss?:\/\//);
      expect(wsUrl).toContain('/ws');
      expect(wsUrl).not.toContain('/api/v1');
    });

    it('should use default API URL if environment variable not set', () => {
      const wsUrl = getConfiguredWebSocketUrl();
      
      // Should fall back to default localhost:8000
      expect(wsUrl).toContain('localhost:8000');
    });
  });
});
