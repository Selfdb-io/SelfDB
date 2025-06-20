import React, { createContext, useState, useEffect, useContext, ReactNode } from 'react';
import { loginUser, registerUser, getCurrentUser, User, LoginResponse } from '../services/authService';
import realtimeService from '../../../services/realtimeService';

// Define the shape of the context
interface AuthContextType {
  currentUser: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string) => Promise<User>;
  logout: () => void;
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
  logout: () => {},
  isAuthenticated: false,
  wsConnected: false,
});

// Props for the provider component
interface AuthProviderProps {
  children: ReactNode;
}

// Custom hook to use the auth context
export const useAuth = () => useContext(AuthContext);

// Provider component
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  // Function to establish WebSocket connection
  const setupWebSocket = (user: User) => {
    if (!user) return;
    
    const token = localStorage.getItem('token');
    if (!token) return;
    
    // Connect to WebSocket if not already connected
    if (!wsConnected) {
      realtimeService.connect(token);
      
      // Subscribe to user-specific updates
      realtimeService.subscribe(`user:${user.id}`, {
        userId: user.id
      });
      
      setWsConnected(true);
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

            // Verify the user is a superuser
            if (!user.is_superuser) {
              console.error('Access denied: Only superusers can access the admin dashboard');
              localStorage.removeItem('token');
              localStorage.removeItem('refreshToken');
              setError('Access denied: Only superusers can access the admin dashboard');
              setCurrentUser(null);
            } else {
              setCurrentUser(user);
              // Setup WebSocket connection after authentication
              setupWebSocket(user);
            }
          } catch (authErr) {
            console.error('Error validating token:', authErr);
            // Error handling is now done in the API interceptor which will attempt
            // to refresh the token automatically if it's expired
          }
        } else {
          console.log('No authentication token found');
        }
      } catch (err) {
        console.error('Error in authentication check:', err);
        // Clear tokens
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
      } finally {
        setLoading(false);
      }
    };

    checkLoggedIn();
    
    // Cleanup WebSocket on app unmount
    return () => {
      realtimeService.disconnect();
      setWsConnected(false);
    };
  }, []);

  // Login function
  const login = async (email: string, password: string): Promise<User> => {
    try {
      setError(null);
      console.log('Attempting login for:', email);

      const { access_token, refresh_token, is_superuser }: LoginResponse = await loginUser(email, password);
      console.log('Login successful, tokens received');

      // Check if user is a superuser - only allow superusers to access the frontend
      if (!is_superuser) {
        console.error('Access denied: Only superusers can access the admin dashboard');
        setError('Access denied: Only superusers can access the admin dashboard');
        throw new Error('Access denied: Only superusers can access the admin dashboard');
      }

      // Store the tokens
      localStorage.setItem('token', access_token);
      localStorage.setItem('refreshToken', refresh_token);
      console.log('Tokens stored in localStorage');

      // Get user info with the new token
      const user = await getCurrentUser();
      console.log('User info retrieved:', user);

      setCurrentUser(user);
      
      // Setup WebSocket connection after login
      setupWebSocket(user);
      
      return user;
    } catch (err: any) {
      console.error('Login error:', err);
      setError(err.response?.data?.detail || err.message || 'Login failed');
      throw err;
    }
  };

  // Register function
  const register = async (email: string, password: string): Promise<User> => {
    try {
      setError(null);
      const user = await registerUser(email, password);
      return user;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed');
      throw err;
    }
  };

  // Logout function
  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    setCurrentUser(null);
    // Disconnect WebSocket on logout
    realtimeService.disconnect();
    setWsConnected(false);
  };

  // Context value
  const value: AuthContextType = {
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
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}; 