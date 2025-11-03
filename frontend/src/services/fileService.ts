import api from './api';

export interface FileItem {
  id: string; // use path relative to bucket as id
  filename: string;
  size: number;
  content_type: string;
  created_at: string;
  updated_at: string;
  bucket?: string;
}

export interface FileWithUrl extends FileItem { download_url: string; }

// New upload returns basic info from backend proxy
export interface UploadResponse {
  success: boolean;
  bucket: string;
  path: string;
  size: number;
  file_id?: string;
  upload_time?: number;
  url?: string;
}

// Get all files for the current user, optionally filtered by bucket
export const getUserFiles = async (_bucketId?: string): Promise<FileItem[]> => {
  // Prefer bucketService.getBucketFiles; keep placeholder for compatibility
  return [];
};

// Upload a file using the new direct upload approach
export const uploadFile = async (file: File, bucket: string, path?: string): Promise<UploadResponse> => {
  const filePath = path || file.name;
  const form = new FormData();
  form.append('file', file);
  form.append('bucket', bucket);
  form.append('path', filePath);
  const response = await api.post('/files/upload', form);
  return response.data;
};

// Get file details with download URL - updated to use new endpoint
export const getFileWithUrl = async (bucket: string, path: string): Promise<FileWithUrl> => {
  const download_url = `${api.defaults.baseURL}/files/${encodeURIComponent(bucket)}/${encodeURIComponent(path)}`;
  return { 
    id: path, 
    filename: path.split('/').pop() || path, 
    size: 0, 
    content_type: 'application/octet-stream', 
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    download_url 
  };
};

// Download a file directly - updated to use the direct URL from download-info
export const downloadFile = async (bucket: string, path: string): Promise<string> => {
  // Return direct URL; nginx injects X-API-Key, so navigation starts streaming immediately
  return `${api.defaults.baseURL}/files/${encodeURIComponent(bucket)}/${encodeURIComponent(path)}`;
};

// Delete a file
export const deleteFile = async (bucket: string, path: string): Promise<void> => {
  await api.delete(`/files/${encodeURIComponent(bucket)}/${encodeURIComponent(path)}`);
};