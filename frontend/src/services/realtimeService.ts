// WebSocket connection management for real-time updates
import api from './api';

// Define types for the realtime service
type MessageCallback = (data: any) => void;
type SubscriptionData = Record<string, any>;

interface WebSocketMessage {
  type: string;
  subscription_id?: string;
  user_id?: string;
  data?: any;
  token?: string;
}

class RealtimeService {
  private socket: WebSocket | null = null;
  private connected: boolean = false;
  private listeners: Map<string, Set<MessageCallback>> = new Map();
  private subscriptions: Map<string, SubscriptionData> = new Map();
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectTimeout: number | null = null;
  private isConnecting: boolean = false;

  // Connect to the WebSocket server
  connect(token: string): void {
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

    // Use the baseURL from the api instance
    const apiUrl = api.defaults.baseURL || '';
    const wsUrl = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://');
    this.socket = new WebSocket(`${wsUrl}/realtime/ws`);

    this.socket.onopen = () => {
      console.log('WebSocket connected');
      this.connected = true;
      this.reconnectAttempts = 0;
      this.isConnecting = false;

      // Authenticate with the server
      if (this.socket) {
        this.socket.send(JSON.stringify({
          type: 'authenticate',
          token: token
        }));
      }

      // Resubscribe to previous subscriptions
      this.subscriptions.forEach((data, id) => {
        this.subscribe(id, data);
      });
    };

    this.socket.onmessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;

        // Handle different message types
        if (message.type === 'connected') {
          console.log('WebSocket authenticated:', message.user_id);
        } else if (message.type === 'subscribed') {
          console.log('Subscribed to:', message.subscription_id);
        } else if (message.type === 'unsubscribed') {
          console.log('Unsubscribed from:', message.subscription_id);
        } else if (message.type === 'database_change' && message.subscription_id && this.listeners.has(message.subscription_id)) {
          // Handle database change notifications
          console.log('Received database change for subscription:', message.subscription_id, message.data);
          const listeners = this.listeners.get(message.subscription_id);
          listeners?.forEach(callback => callback(message.data));
        } else if (message.subscription_id && this.listeners.has(message.subscription_id)) {
          // Notify listeners for this subscription
          const listeners = this.listeners.get(message.subscription_id);
          listeners?.forEach(callback => callback(message.data));
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
      // or another genuine disconnect
      if (event.code === 1005) {
        // 1005 is a clean close by the browser during page navigation
        // Reconnect immediately with a short delay
        console.log(`Attempting to reconnect in 2000ms...`);
        if (this.reconnectTimeout !== null) {
          window.clearTimeout(this.reconnectTimeout);
        }
        this.reconnectTimeout = window.setTimeout(() => {
          this.connect(token);
        }, 2000);
        return;
      }

      // For other disconnect reasons, use exponential backoff
      if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
        console.log(`Attempting to reconnect in ${delay}ms...`);

        if (this.reconnectTimeout !== null) {
          window.clearTimeout(this.reconnectTimeout);
        }
        this.reconnectTimeout = window.setTimeout(() => {
          this.connect(token);
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
    }
  }

  // Subscribe to a specific data channel
  subscribe(subscriptionId: string, data: SubscriptionData = {}): boolean {
    if (!this.connected || !this.socket) {
      // Store subscription for when we reconnect
      this.subscriptions.set(subscriptionId, data);
      return false;
    }

    this.socket.send(JSON.stringify({
      type: 'subscribe',
      subscription_id: subscriptionId,
      data: data
    }));

    this.subscriptions.set(subscriptionId, data);
    return true;
  }

  // Unsubscribe from a specific data channel
  unsubscribe(subscriptionId: string): boolean {
    if (!this.connected || !this.socket) {
      this.subscriptions.delete(subscriptionId);
      return false;
    }

    this.socket.send(JSON.stringify({
      type: 'unsubscribe',
      subscription_id: subscriptionId
    }));

    this.subscriptions.delete(subscriptionId);
    return true;
  }

  // Add a listener for a specific subscription
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

  // Remove a listener for a specific subscription
  removeListener(subscriptionId: string, callback: MessageCallback): void {
    if (this.listeners.has(subscriptionId)) {
      this.listeners.get(subscriptionId)?.delete(callback);

      // Clean up if no listeners remain
      if (this.listeners.get(subscriptionId)?.size === 0) {
        this.listeners.delete(subscriptionId);
      }
    }
  }
}

// Create a singleton instance
const realtimeService = new RealtimeService();
export default realtimeService;