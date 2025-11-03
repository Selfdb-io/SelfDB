import api from './api';
import realtimeService from './realtimeService';

export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login_at?: string;
  isDeleting?: boolean; // UI state for deletion operations
}

// Add a type for user creation that includes password
export interface UserCreate {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

// Add a type for user updates (admin only)
export interface UserUpdate {
  email?: string;
  role?: string;
  is_active?: boolean;
}

interface PasswordChangeData {
  current_password: string;
  new_password: string;
}

// Get all users
export const getUsers = async (): Promise<User[]> => {
  const response = await api.get('/users/');
  // Ensure newest users come first
  const users: User[] = response.data.users || [];
  return users.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
};

// Get all regular users (excluding admins)
export const getRegularUsers = async (): Promise<User[]> => {
  const response = await api.get('/users/');
  // Filter out admins
  const users: User[] = (response.data.users || []).filter((user: User) => user.role !== 'ADMIN');
  // Return newest first so UI shows recent signups at the top
  return users.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
};

// Get regular users with pagination (excluding admins)
export const getRegularUsersPaginated = async (page: number = 1, pageSize: number = 100): Promise<{ data: User[], total: number, page: number, pageSize: number, totalPages: number }> => {
  // Get all users first to filter and paginate properly
  const response = await api.get('/users/', {
    params: {
      offset: 0,
      limit: 1000 // Get a large number to ensure we get all users for filtering
    }
  });
  
  // Filter out admins
  const regularUsers: User[] = (response.data.users || []).filter((user: User) => user.role !== 'ADMIN');

  // Sort by created_at descending so page 1 contains the most recently created users
  regularUsers.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  
  // Calculate pagination
  const total = regularUsers.length;
  const totalPages = Math.ceil(total / pageSize);
  const startIndex = (page - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const data = regularUsers.slice(startIndex, endIndex);
  
  return {
    data,
    total,
    page,
    pageSize,
    totalPages
  };
};

// Get a specific user by ID
export const getUserById = async (userId: string): Promise<User> => {
  const response = await api.get(`/users/${userId}`);
  return response.data;
};

// Update a user
export const updateUser = async (userId: string, userData: UserUpdate): Promise<User> => {
  const response = await api.put(`/users/${userId}`, userData);
  return response.data;
};

// Delete a user
export const deleteUser = async (userId: string): Promise<void> => {
  await api.delete(`/users/${userId}`);
};

// Change password for current user
export const changePassword = async (passwordData: PasswordChangeData): Promise<void> => {
  await api.post('/auth/change-password', passwordData);
};

// Get count of regular users (excluding admins)
export const getRegularUsersCount = async (): Promise<number> => {
  const response = await api.get('/users/');
  // Filter out admins and return count
  return (response.data.users || []).filter((user: User) => user.role !== 'ADMIN').length;
};

// Subscribe to real-time user count updates
export const subscribeToUserCountUpdates = (callback: (count: number) => void): (() => void) => {
  const subscriptionId = 'user_count_updates';

  // Subscribe to user changes that might affect the count
  realtimeService.subscribe(subscriptionId, {
    resource_type: 'users',
    resource_id: '*',
    filters: { role: 'neq.ADMIN' } // Only listen to regular users
  });

  // Add listener for user count changes
  const removeListener = realtimeService.addListener(subscriptionId, async () => {
    // When users are added, updated, or deleted, refetch the count
    try {
      const newCount = await getRegularUsersCount();
      callback(newCount);
    } catch (error) {
      console.error('Error fetching updated user count:', error);
    }
  });

  // Return unsubscribe function
  return () => {
    removeListener();
    realtimeService.unsubscribe(subscriptionId);
  };
};

// Subscribe to real-time regular users list updates
export const subscribeToRegularUsersUpdates = (callback: (users: User[]) => void): (() => void) => {
  const subscriptionId = 'regular_users_updates';

  // Subscribe to user changes for regular users only
  realtimeService.subscribe(subscriptionId, {
    resource_type: 'users',
    resource_id: '*',
    filters: { role: 'neq.ADMIN' }
  });

  // Add listener for user list changes
  const removeListener = realtimeService.addListener(subscriptionId, async () => {
    // When users are added, updated, or deleted, refetch the list
    try {
      const updatedUsers = await getRegularUsers();
      callback(updatedUsers);
    } catch (error) {
      console.error('Error fetching updated users list:', error);
    }
  });

  // Return unsubscribe function
  return () => {
    removeListener();
    realtimeService.unsubscribe(subscriptionId);
  };
};

// Subscribe to all user updates (including superusers)
export const subscribeToAllUsersUpdates = (callback: (users: User[]) => void): (() => void) => {
  const subscriptionId = 'all_users_updates';
  
  // Subscribe to all user changes
  realtimeService.subscribe(subscriptionId, {
    table: 'users'
  });

  // Add listener for user list changes
  const removeListener = realtimeService.addListener(subscriptionId, async () => {
    // When users are added, updated, or deleted, refetch the list
    try {
      const updatedUsers = await getUsers();
      callback(updatedUsers);
    } catch (error) {
      console.error('Error fetching updated users list:', error);
    }
  });

  // Return unsubscribe function
  return () => {
    removeListener();
    realtimeService.unsubscribe(subscriptionId);
  };
};

// Create a new user
export const createUser = async (userData: UserCreate): Promise<User> => {
  // For user creation, we need to call the register endpoint with additional fields
  const registerData = {
    email: userData.email,
    password: userData.password,
    first_name: userData.first_name,
    last_name: userData.last_name
  };
  
  const response = await api.post('/auth/register', registerData);
  // The response will contain a token and user data, we just want the user data
  return response.data.user;
};

// Admin: set/reset another user's password
export const adminSetUserPassword = async (userId: string, newPassword: string): Promise<{ message: string }> => {
  // `api` already has baseURL set to the API root (e.g. '/api/v1'),
  // so don't duplicate the '/api/v1' segment in request paths.
  const response = await api.post(`/users/${userId}/password`, {
    new_password: newPassword
  });
  return response.data;
};

export default {
  getUsers,
  getRegularUsers,
  getRegularUsersPaginated,
  getUserById,
  updateUser,
  deleteUser,
  changePassword,
  createUser,
  adminSetUserPassword
};