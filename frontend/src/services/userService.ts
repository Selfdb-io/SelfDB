import api from './api';
import realtimeService from './realtimeService';

interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

// Add a type for user creation that includes password
export interface UserCreate {
  email: string;
  password: string;
  is_active: boolean;
  is_superuser: boolean;
}

interface PasswordChangeData {
  current_password: string;
  new_password: string;
}

// Get all users
export const getUsers = async (): Promise<User[]> => {
  const response = await api.get('/users/');
  return response.data;
};

// Get all regular users (excluding superusers/admins)
export const getRegularUsers = async (): Promise<User[]> => {
  const response = await api.get('/users/');
  // Filter out superusers/admins
  return response.data.filter((user: User) => !user.is_superuser);
};

// Get regular users with pagination (excluding superusers/admins)
export const getRegularUsersPaginated = async (page: number = 1, pageSize: number = 100): Promise<{ data: User[], total: number, page: number, pageSize: number, totalPages: number }> => {
  // Get all users first to filter and paginate properly
  const response = await api.get('/users/', {
    params: {
      skip: 0,
      limit: 1000 // Get a large number to ensure we get all users for filtering
    }
  });
  
  // Filter out superusers/admins
  const regularUsers = response.data.filter((user: User) => !user.is_superuser);
  
  // Apply pagination to the filtered results
  const startIndex = (page - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedUsers = regularUsers.slice(startIndex, endIndex);
  
  return {
    data: paginatedUsers,
    total: regularUsers.length,
    page,
    pageSize,
    totalPages: Math.ceil(regularUsers.length / pageSize)
  };
};

// Get total count of regular users (excluding superusers/admins) with real-time updates
export const getRegularUsersCount = async (): Promise<number> => {
  const response = await api.get('/users/count');
  return response.data;
};

// Get a specific user by ID
export const getUser = async (userId: string): Promise<User> => {
  const response = await api.get(`/users/${userId}`);
  return response.data;
};

// Get current user information
export const getCurrentUser = async (): Promise<User> => {
  const response = await api.get('/users/me');
  return response.data;
};

// Create a new user
export const createUser = async (userData: UserCreate): Promise<User> => {
  const response = await api.post('/users', userData);
  return response.data;
};

// Update a user
export const updateUser = async (userId: string, userData: Partial<User>): Promise<User> => {
  const response = await api.put(`/users/${userId}`, userData);
  return response.data;
};

// Update current user
export const updateCurrentUser = async (userData: Partial<User>): Promise<User> => {
  const response = await api.put('/users/me', userData);
  return response.data;
};

// Delete a user
export const deleteUser = async (userId: string): Promise<void> => {
  const response = await api.delete(`/users/${userId}`);
  return response.data;
};

// Change current user's password
export const changePassword = async (passwordData: PasswordChangeData): Promise<void> => {
  const response = await api.put('/users/me/password', passwordData);
  return response.data;
};

// Subscribe to real-time user count updates
export const subscribeToUserCountUpdates = (callback: (count: number) => void): (() => void) => {
  const subscriptionId = 'user_count_updates';
  
  // Subscribe to user changes that might affect the count
  realtimeService.subscribe(subscriptionId, {
    table: 'users',
    filter: 'is_superuser.eq.false' // Only listen to regular users
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
    table: 'users',
    filter: 'is_superuser.eq.false'
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