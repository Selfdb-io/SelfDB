import React, { createContext, useState, useEffect, useContext } from 'react';
import { loginUser, registerUser, getCurrentUser, logoutUser, User, LoginResponse } from '../services/authService';
import { parseBackendError } from '../../../utils/errorParser';
import realtimeService from '../../../services/realtimeService';
import { startTokenRefreshManager, stopTokenRefreshManager } from '../../../utils/tokenRefreshManager';

// Define the shape of the context
interface AuthContextType {
  currentUser: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string, firstName: string, lastName: string) => Promise<User>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  wsConnected: boolean;
}

// Create the context with default values
const AuthContext = createContext<AuthContextType>({
  currentUser: null,
  loading: true,
  error: null,
  login: async () => {
    throw new Error('login function not implemented');
  },
  register: async () => {
    throw new Error('register function not implemented');
  },
  logout: async () => {},
  isAuthenticated: false,
  wsConnected: false,
});

// Props for the provider component
interface AuthProviderProps {
  children: React.ReactNode;
}

// Custom hook to use the auth context
export const useAuth = () => useContext(AuthContext);

// Provider component
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  // Function to establish WebSocket connection and start token refresh manager
  const setupWebSocket = (user: User) => {
    if (!user) return;

    const token = localStorage.getItem('token');
    if (!token) return;

    // Connect to WebSocket if not already connected
    if (!wsConnected) {
      realtimeService.connect(token);

      // Subscribe to user-specific updates
      realtimeService.subscribe(`user:${user.id}`, {
        resource_type: 'users',
        resource_id: user.id,
        filters: {}
      });

      setWsConnected(true);
    }

    // Start proactive token refresh manager to keep user logged in
    startTokenRefreshManager();
  };

  // Login function
  const login = async (email: string, password: string): Promise<User> => {
    try {
      setLoading(true);
      setError(null);

      // Login user and get tokens
      const response: LoginResponse = await loginUser(email, password);

      // Store tokens in localStorage
      localStorage.setItem('token', response.access_token);
      localStorage.setItem('refreshToken', response.refresh_token);

      // User data comes from the response
      const user = response.user;

      // Verify the user is a superuser/admin
      if (!user.is_active || user.role !== 'ADMIN') {
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        throw new Error('Access denied: Only active admin users can access the admin dashboard');
      }

      setCurrentUser(user);
      setupWebSocket(user);

      return user;
    } catch (err) {
      const parsedError = parseBackendError(err);
      setError(parsedError.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Register function
  const register = async (email: string, password: string, firstName: string, lastName: string): Promise<User> => {
    try {
      setLoading(true);
      setError(null);

      // Register user
      const response = await registerUser(email, password, firstName, lastName);
      const user = response.user;

      return user;
    } catch (err) {
      const parsedError = parseBackendError(err);
      setError(parsedError.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = async (): Promise<void> => {
    try {
      const accessToken = localStorage.getItem('token');
      const refreshToken = localStorage.getItem('refreshToken');

      // Stop token refresh manager
      stopTokenRefreshManager();

      // Call backend logout endpoint
      await logoutUser(accessToken || undefined, refreshToken || undefined);
    } catch (err) {
      console.error('Error during logout:', err);
      // Continue with local cleanup even if backend call fails
    } finally {
      // Clean up local state
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      setCurrentUser(null);
      setError(null);

      // Disconnect WebSocket
      realtimeService.disconnect();
      setWsConnected(false);
    }
  };

  // Check if user is already logged in on mount
  useEffect(() => {
    const checkLoggedIn = async () => {
      try {
        const token = localStorage.getItem('token');
        console.log('Checking authentication on app load, token exists:', !!token);

        if (token) {
          try {
            const user = await getCurrentUser();
            console.log('User authenticated successfully:', user);

            // Verify the user is active and admin
            if (!user.is_active || user.role !== 'ADMIN') {
              console.error('Access denied: Only active admin users can access the admin dashboard');
              localStorage.removeItem('token');
              localStorage.removeItem('refreshToken');
              stopTokenRefreshManager();
              setError('Access denied: Only active admin users can access the admin dashboard');
              setCurrentUser(null);
            } else {
              setCurrentUser(user);
              // Setup WebSocket connection and token refresh manager after authentication
              setupWebSocket(user);
            }
          } catch (authErr) {
            console.error('Error validating token:', authErr);
            // Clear local state when token validation fails
            localStorage.removeItem('token');
            localStorage.removeItem('refreshToken');
            stopTokenRefreshManager();
            setCurrentUser(null);
            setError('Authentication failed. Please log in again.');
            // API interceptor will handle redirect if needed
          }
        } else {
          console.log('No authentication token found');
        }
      } catch (err) {
        console.error('Error checking logged in status:', err);
        setError('Failed to check authentication status');
      } finally {
        setLoading(false);
      }
    };

    checkLoggedIn();

    // Cleanup on unmount
    return () => {
      stopTokenRefreshManager();
    };
  }, []);

  // Context values
  const contextValue: AuthContextType = {
    currentUser,
    loading,
    error,
    login,
    register,
    logout,
    isAuthenticated: !!currentUser,
    wsConnected
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};