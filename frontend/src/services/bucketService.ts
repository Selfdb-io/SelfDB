import api from './api';
import { deleteFile } from './fileService';

// Define types
export interface Bucket {
  id: string; // use name as id for storage-backed buckets
  name: string;
  description?: string;
  is_public: boolean;
  file_count: number;
  total_size: number;
  created_at: number;
  updated_at: number;
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
  const data = response.data;
  const list = Array.isArray(data) ? data : (data.buckets || []);
  return list.map((b: any) => ({
    id: b.name,
    name: b.name,
    description: b.description || '',
    is_public: b.public ?? b.is_public ?? false,
    file_count: b.file_count ?? 0,
    total_size: b.total_size ?? 0,
    created_at: Number(b.created_at ?? Date.now()),
    updated_at: Number(b.updated_at ?? Date.now()),
  }));
};

// Get a specific bucket by ID
export const getBucket = async (bucketId: string): Promise<Bucket> => {
  const response = await api.get(`/buckets/${bucketId}`);
  const data = response.data.bucket || response.data;
  return {
    id: data.name,
    name: data.name,
    description: data.description || '',
    is_public: data.public ?? data.is_public ?? false,
    file_count: data.file_count ?? 0,
    total_size: data.total_size ?? 0,
    created_at: Number(data.created_at ?? Date.now()),
    updated_at: Number(data.updated_at ?? Date.now()),
  };
};

// Create a new bucket
export const createBucket = async (bucketData: CreateBucketData): Promise<Bucket> => {
  const payload = { name: bucketData.name, public: bucketData.is_public ?? false };
  const response = await api.post('/buckets', payload);
  const data = response.data.bucket || response.data;
  return {
    id: data.name,
    name: data.name,
    description: data.description || '',
    is_public: data.public ?? false,
    file_count: 0,
    total_size: 0,
    created_at: Number(Date.now()),
    updated_at: Number(Date.now()),
  };
};

// Update a bucket
export const updateBucket = async (bucketId: string, bucketData: Partial<CreateBucketData>): Promise<Bucket> => {
  const payload: any = {};
  if (bucketData.is_public !== undefined) payload.public = bucketData.is_public;
  const response = await api.put(`/buckets/${bucketId}`, payload);
  const data = response.data.bucket || response.data;
  return {
    id: data.name,
    name: data.name,
    description: data.description || '',
    is_public: data.public ?? false,
    file_count: 0,
    total_size: 0,
    created_at: Number(Date.now()),
    updated_at: Number(Date.now()),
  };
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

export const getBucketFiles = async (bucketId: string, _params: FileListParams = {}): Promise<BucketFile[]> => {
  const response = await api.get(`/buckets/${bucketId}/files`);
  const data = response.data.files || response.data;
  return data.map((f: any) => ({
    id: f.id || f.path || f.filename,
    filename: f.filename,
    size: f.size ?? 0,
    content_type: f.content_type || 'application/octet-stream',
    // Normalize timestamps to ISO strings; backend returns seconds since epoch
    created_at: (() => {
      const v = f.created_at;
      if (v == null) return '';
      const n = Number(v);
      const ms = Number.isFinite(n) ? (n < 1e12 ? n * 1000 : n) : Date.parse(String(v));
      const d = new Date(ms);
      return isNaN(d.getTime()) ? '' : d.toISOString();
    })(),
    updated_at: (() => {
      const v = f.updated_at;
      if (v == null) return '';
      const n = Number(v);
      const ms = Number.isFinite(n) ? (n < 1e12 ? n * 1000 : n) : Date.parse(String(v));
      const d = new Date(ms);
      return isNaN(d.getTime()) ? '' : d.toISOString();
    })(),
  }));
};

// New function to delete a bucket and all its contents
export const deleteBucketAndContents = async (bucketId: string): Promise<void> => {
  // Fetch current files and delete them first
  const files = await getBucketFiles(bucketId);
  if (files.length) {
    await Promise.all(files.map(file => deleteFile(bucketId, file.id)));
  }
  // Then delete the bucket
  await deleteBucket(bucketId);
};