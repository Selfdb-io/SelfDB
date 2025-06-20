import api from './api';

// Define types
export interface Bucket {
  id: string;
  name: string;
  description?: string;
  is_public: boolean;
  file_count: number;
  total_size: number;
  created_at: string;
  updated_at: string;
}

export interface CreateBucketData {
  name: string;
  description?: string;
  is_public?: boolean;
}

export interface BucketFile {
  id: string;
  filename: string;
  size: number;
  content_type: string;
  created_at: string;
  updated_at: string;
}

// Get all buckets for the current user
export const getUserBuckets = async (): Promise<Bucket[]> => {
  const response = await api.get('/buckets');
  return response.data;
};

// Get a specific bucket by ID
export const getBucket = async (bucketId: string): Promise<Bucket> => {
  const response = await api.get(`/buckets/${bucketId}`);
  return response.data;
};

// Create a new bucket
export const createBucket = async (bucketData: CreateBucketData): Promise<Bucket> => {
  const response = await api.post('/buckets', bucketData);
  return response.data;
};

// Update a bucket
export const updateBucket = async (bucketId: string, bucketData: Partial<CreateBucketData>): Promise<Bucket> => {
  const response = await api.put(`/buckets/${bucketId}`, bucketData);
  return response.data;
};

// Delete a bucket
export const deleteBucket = async (bucketId: string): Promise<void> => {
  await api.delete(`/buckets/${bucketId}`);
};

// Get files in a bucket
export interface FileListParams {
  skip?: number;
  limit?: number;
}

export const getBucketFiles = async (bucketId: string, params: FileListParams = {}): Promise<BucketFile[]> => {
  const { skip = 0, limit = 100 } = params;
  const response = await api.get(`/buckets/${bucketId}/files`, {
    params: { skip, limit }
  });
  return response.data;
}; 