// Define types aligned with Phoenix backend WebSocket protocol
type MessageCallback = (data: any) => void;
type SubscriptionData = Record<string, any>;

import { getApiBaseUrl } from './api';
const getApiUrl = (): string => getApiBaseUrl();

// Phoenix v2 JSON serializer uses array frames: [join_ref, ref, topic, event, payload]
type PhoenixClientFrame = [string | null, string | null, string, string, Record<string, any>];

class RealtimeService {
  private socket: WebSocket | null = null;
  private connected: boolean = false;
  private listeners: Map<string, Set<MessageCallback>> = new Map();
  private subscriptions: Set<string> = new Set(); // Channel topics we've joined
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectTimeout: number | null = null;
  private isConnecting: boolean = false;
  private joinRefCounter: number = 0;
  private currentToken: string | null = null;

  // Connect to the WebSocket server
  connect(token: string): void {
    // Store token for reconnection
    this.currentToken = token;
    
    if (this.isConnecting) {
      return; // Prevent multiple connection attempts
    }

    if (this.socket && this.connected) {
      return; // Already connected
    }

    this.isConnecting = true;

    if (this.socket) {
      this.disconnect();
    }

        // Use the configured API URL and construct WebSocket URL with token
        const apiUrl = getApiUrl();
        const wsUrl = `${apiUrl.replace(/^http/, 'ws')}/realtime/ws?token=${encodeURIComponent(token)}`;

        console.log('Connecting to Phoenix WebSocket:', wsUrl.replace(token, '***TOKEN***'));
    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      console.log('WebSocket connected to Phoenix');
      this.connected = true;
      this.reconnectAttempts = 0;
      this.isConnecting = false;

      // Rejoin all previous subscriptions
      this.subscriptions.forEach(topic => {
        this.joinChannel(topic);
      });
    };

    this.socket.onmessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data);
        
        console.log('Received message:', message);

        // Handle different message types from backend proxy
        if (message.type === 'subscribed') {
          console.log('Successfully subscribed to:', message.topic);
          this.subscriptions.add(message.topic);
        } else if (message.type === 'subscription_status') {
          console.log('Subscription status update:', message.topic, message.status);
        } else if (message.type === 'broadcast') {
          console.log('Received broadcast on channel:', message.channel, message.payload);
          if (this.listeners.has(message.channel)) {
            const listeners = this.listeners.get(message.channel);
            listeners?.forEach(callback => callback(message.payload));
          }
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.socket.onclose = (event: CloseEvent) => {
      this.connected = false;
      this.isConnecting = false;

      console.log('WebSocket disconnected:', event.code, event.reason);

      // Check if this is a navigation-related disconnect (code 1005)
      if (event.code === 1005) {
        console.log(`Attempting to reconnect in 2000ms...`);
        if (this.reconnectTimeout !== null) {
          window.clearTimeout(this.reconnectTimeout);
        }
        this.reconnectTimeout = window.setTimeout(() => {
          if (this.currentToken) {
            this.connect(this.currentToken);
          }
        }, 2000);
        return;
      }

      // For other disconnect reasons, use exponential backoff
      if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
        console.log(`Attempting to reconnect in ${delay}ms...`);

        this.reconnectTimeout = window.setTimeout(() => {
          if (this.currentToken) {
            this.connect(this.currentToken);
          }
        }, delay);
      }
    };

    this.socket.onerror = (error: Event) => {
      console.error('WebSocket error:', error);
      this.isConnecting = false;
    };
  }

  // Disconnect from the WebSocket server
  disconnect(): void {
    if (this.reconnectTimeout !== null) {
      window.clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.socket) {
      this.socket.close();
      this.socket = null;
      this.connected = false;
      this.isConnecting = false;
      this.subscriptions.clear();
    }
  }

      // Helper method to join a Phoenix channel
      private joinChannel(topic: string): void {
        if (!this.connected || !this.socket) {
          console.warn('Cannot join channel, not connected');
          return;
        }

        // Send subscription message in the format expected by backend proxy
        const subscriptionMessage = {
          type: 'subscribe',
          resource_type: topic.replace('_events', ''),
          resource_id: null
        };

        console.log('Joining Phoenix channel:', topic, subscriptionMessage);
        this.socket.send(JSON.stringify(subscriptionMessage));
      }

  // Subscribe to a specific channel (e.g., 'tables_events', 'files_events')
  subscribe(subscriptionId: string, _data: SubscriptionData = {}): boolean {
    // Store subscription for when we reconnect
    this.subscriptions.add(subscriptionId);
    
    if (!this.connected || !this.socket) {
      return false;
    }

    // Join the Phoenix channel
    this.joinChannel(subscriptionId);
    return true;
  }

      // Unsubscribe from a specific channel
      unsubscribe(subscriptionId: string): boolean {
        this.subscriptions.delete(subscriptionId);
        
        if (!this.connected || !this.socket) {
          return false;
        }

        // Send unsubscribe message in the format expected by backend proxy
        const unsubscribeMessage = {
          type: 'unsubscribe',
          resource_type: subscriptionId.replace('_events', ''),
          resource_id: null
        };

        console.log('Unsubscribing from Phoenix channel:', subscriptionId, unsubscribeMessage);
        this.socket.send(JSON.stringify(unsubscribeMessage));
        return true;
      }

  // Send ping to keep connection alive
  ping(): boolean {
    if (!this.connected || !this.socket) {
      return false;
    }

    const ref = (++this.joinRefCounter).toString();
    
    const frame: PhoenixClientFrame = [ref, ref, 'phoenix', 'heartbeat', {}];
    this.socket.send(JSON.stringify(frame));
    return true;
  }

  // Add a listener for a specific channel
  addListener(subscriptionId: string, callback: MessageCallback): () => void {
    if (!this.listeners.has(subscriptionId)) {
      this.listeners.set(subscriptionId, new Set());
    }

    this.listeners.get(subscriptionId)?.add(callback);

    // Return a function to remove this listener
    return () => {
      this.removeListener(subscriptionId, callback);
    };
  }

  // Remove a listener for a specific channel
  removeListener(subscriptionId: string, callback: MessageCallback): void {
    if (this.listeners.has(subscriptionId)) {
      this.listeners.get(subscriptionId)?.delete(callback);

      // Clean up if no listeners remain
      if (this.listeners.get(subscriptionId)?.size === 0) {
        this.listeners.delete(subscriptionId);
      }
    }
  }

  // Get connection status
  getConnectionStatus(): { connected: boolean } {
    return {
      connected: this.connected
    };
  }
}

// Create a singleton instance
const realtimeService = new RealtimeService();
export default realtimeService;