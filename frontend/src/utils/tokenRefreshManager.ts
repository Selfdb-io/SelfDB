/**
 * Token Refresh Manager
 * 
 * Proactively refreshes JWT tokens before they expire to keep users logged in.
 * Decodes JWT tokens to check expiration and refreshes 5 minutes before expiry.
 */

import { refreshToken } from '../modules/auth/services/tokenRefresh';

// Refresh tokens 5 minutes before they expire
const REFRESH_BUFFER_MS = 5 * 60 * 1000; // 5 minutes in milliseconds

// Check token expiration every minute
const CHECK_INTERVAL_MS = 60 * 1000; // 1 minute

let refreshCheckInterval: NodeJS.Timeout | null = null;

/**
 * Decode JWT token without verification (frontend only needs to read expiration)
 */
function decodeJWT(token: string): { exp?: number; iat?: number } | null {
  try {
    const base64Url = token.split('.')[1];
    if (!base64Url) return null;
    
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    
    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error('Failed to decode JWT:', error);
    return null;
  }
}

/**
 * Check if token needs refresh
 */
function shouldRefreshToken(token: string): boolean {
  const decoded = decodeJWT(token);
  if (!decoded || !decoded.exp) {
    return false;
  }
  
  const expirationTime = decoded.exp * 1000; // Convert to milliseconds
  const currentTime = Date.now();
  const timeUntilExpiration = expirationTime - currentTime;
  
  // Refresh if token expires in less than REFRESH_BUFFER_MS
  return timeUntilExpiration <= REFRESH_BUFFER_MS && timeUntilExpiration > 0;
}

/**
 * Perform token refresh
 */
async function performTokenRefresh(): Promise<boolean> {
  try {
    const refreshTokenStr = localStorage.getItem('refreshToken');
    if (!refreshTokenStr) {
      console.log('No refresh token available for proactive refresh');
      stopTokenRefreshManager();
      return false;
    }
    
    // Check if refresh token itself is expired
    const refreshDecoded = decodeJWT(refreshTokenStr);
    if (refreshDecoded && refreshDecoded.exp) {
      const refreshExpTime = refreshDecoded.exp * 1000;
      if (refreshExpTime <= Date.now()) {
        console.log('Refresh token expired, stopping proactive refresh');
        stopTokenRefreshManager();
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
        return false;
      }
    }
    
    console.log('Proactively refreshing token...');
    const response = await refreshToken(refreshTokenStr);
    
    // Store both tokens
    localStorage.setItem('token', response.access_token);
    localStorage.setItem('refreshToken', response.refresh_token);
    
    console.log('Token refreshed successfully');
    return true;
  } catch (error) {
    console.error('Proactive token refresh failed:', error);
    
    // If refresh fails, stop the manager and redirect to login
    stopTokenRefreshManager();
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    window.location.href = '/login';
    return false;
  }
}

/**
 * Check tokens and refresh if needed
 */
async function checkAndRefreshTokens(): Promise<void> {
  const accessToken = localStorage.getItem('token');
  
  if (!accessToken) {
    console.log('No access token found, stopping token refresh manager');
    stopTokenRefreshManager();
    return;
  }
  
  if (shouldRefreshToken(accessToken)) {
    await performTokenRefresh();
  }
}

/**
 * Start the token refresh manager
 * Call this after successful login/authentication
 */
export function startTokenRefreshManager(): void {
  // Clear any existing interval
  if (refreshCheckInterval) {
    clearInterval(refreshCheckInterval);
  }
  
  console.log('Starting token refresh manager');
  
  // Check immediately
  checkAndRefreshTokens();
  
  // Then check periodically
  refreshCheckInterval = setInterval(checkAndRefreshTokens, CHECK_INTERVAL_MS);
}

/**
 * Stop the token refresh manager
 * Call this on logout
 */
export function stopTokenRefreshManager(): void {
  if (refreshCheckInterval) {
    console.log('Stopping token refresh manager');
    clearInterval(refreshCheckInterval);
    refreshCheckInterval = null;
  }
}

/**
 * Get time until token expiration (in milliseconds)
 */
export function getTokenExpirationTime(token: string): number | null {
  const decoded = decodeJWT(token);
  if (!decoded || !decoded.exp) {
    return null;
  }
  
  const expirationTime = decoded.exp * 1000;
  const currentTime = Date.now();
  return expirationTime - currentTime;
}
