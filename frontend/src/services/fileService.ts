import api from './api';

export interface FileItem {
  id: string;
  filename: string;
  size: number;
  content_type: string;
  created_at: string;
  updated_at: string;
  bucket_id: string;
}

export interface FileWithUrl extends FileItem {
  download_url: string;
}

export interface PresignedUploadInfo {
  upload_url: string;
  upload_method: string;
}

export interface FileUploadInitiateResponse {
  file_metadata: FileItem;
  presigned_upload_info: PresignedUploadInfo;
}

// Get all files for the current user, optionally filtered by bucket
export const getUserFiles = async (bucketId?: string): Promise<FileItem[]> => {
  const params = bucketId ? { bucket_id: bucketId } : {};
  const response = await api.get('/files', { params });
  return response.data;
};

// Upload a file using the new direct upload approach
export const uploadFile = async (file: File, bucketId: string): Promise<FileItem> => {
  console.log(`Initiating upload for file: ${file.name}, size: ${file.size}, type: ${file.type}`);
  
  // Step 1: Initiate the upload to get a presigned URL
  const initiateResponse = await api.post<FileUploadInitiateResponse>('/files/initiate-upload', {
    filename: file.name,
    content_type: file.type,
    size: file.size,
    bucket_id: bucketId
  });
  
  // Extract response data
  const { file_metadata, presigned_upload_info } = initiateResponse.data;
  const { upload_url, upload_method } = presigned_upload_info;
  
  console.log(`Got presigned URL: ${upload_url}, method: ${upload_method}`);
  
  // Step 2: Upload the file directly to the storage service using the presigned URL
  try {
    // Create a request with the appropriate method (usually PUT)
    const uploadMethod = upload_method.toLowerCase();
    
    console.log(`Sending ${uploadMethod} request to ${upload_url}`);
    
    // Get the access token for authentication
    const accessToken = localStorage.getItem('accessToken');
    
    // Try using FormData instead of raw file body - this might resolve the 422 error
    const formData = new FormData();
    formData.append('file', file);
    
    // Use fetch API for more direct control over the request
    const uploadResponse = await fetch(upload_url, {
      method: uploadMethod,
      // Try two different approaches - first try the FormData approach
      body: formData, // Instead of direct file
      headers: {
        // Don't set Content-Type with FormData - browser will set it with boundary
        // 'Content-Type': file.type,
        // Add authentication token in case it's needed
        ...(accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {})
      },
    });
    
    if (!uploadResponse.ok) {
      // Try to get more detailed error message
      let errorDetail = '';
      try {
        const errorResponse = await uploadResponse.json();
        errorDetail = JSON.stringify(errorResponse);
      } catch (parseError) {
        errorDetail = await uploadResponse.text();
      }
      
      console.error('Upload failed with response:', {
        status: uploadResponse.status,
        statusText: uploadResponse.statusText,
        detail: errorDetail
      });
      
      throw new Error(`Storage service upload failed: ${uploadResponse.status} ${uploadResponse.statusText}${errorDetail ? ` - ${errorDetail}` : ''}`);
    }
    
    console.log(`Upload successful, returning file metadata for ${file_metadata.id}`);
    
    // Return the file metadata
    return file_metadata;
  } catch (error) {
    console.error('Error during direct upload to storage service:', error);
    // If the direct upload fails, we might want to delete the file record or mark it as failed
    try {
      // Clean up the file record since upload failed
      await api.delete(`/files/${file_metadata.id}`);
      console.log(`Cleaned up file record ${file_metadata.id} after failed upload`);
    } catch (cleanupError) {
      console.error('Failed to clean up file record after upload error:', cleanupError);
    }
    throw error;
  }
};

// Get file details with download URL - updated to use new endpoint
export const getFileWithUrl = async (fileId: string): Promise<FileWithUrl> => {
  const response = await api.get(`/files/${fileId}/download-info`);
  return response.data;
};

// Download a file directly - updated to use the direct URL from download-info
export const downloadFile = async (fileId: string): Promise<string> => {
  try {
    // First, get the download info which includes the direct URL
    const downloadResponse = await api.get(`/files/${fileId}/download-info`);
    const downloadInfo = downloadResponse.data;
    
    // Extract and fix the download URL if needed
    let downloadUrl = downloadInfo.download_url;
    
    // Fix for Docker container name resolution issue - replace storage_service with localhost
    if (downloadUrl.includes('storage_service:')) {
      downloadUrl = downloadUrl.replace('storage_service:', 'localhost:');
      console.log(`Modified download URL to: ${downloadUrl}`);
    }
    
    console.log(`Downloading file from: ${downloadUrl}`);
    
    // Get the authentication token from localStorage
    const accessToken = localStorage.getItem('token');
    
    // Get the actual file content by making a direct request to the storage service
    const response = await fetch(downloadUrl, {
      method: 'GET',
      // Include auth header for authentication with storage service
      headers: {
        ...(accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {}),
      },
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Download error details:', {
        status: response.status,
        statusText: response.statusText,
        body: errorText
      });
      throw new Error(`Failed to download from storage service: ${response.status} ${response.statusText}`);
    }
    
    // Create a blob URL from the response data
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  } catch (error: any) {
    console.error('Error downloading file:', error);
    
    // Provide more detailed error message based on the type of error
    if (error.response?.data?.detail) {
      throw new Error(`Server error: ${error.response.data.detail}`);
    } else if (error.message) {
      throw new Error(error.message);
    } else {
      throw new Error('Unknown error occurred during download');
    }
  }
};

// Delete a file
export const deleteFile = async (fileId: string): Promise<void> => {
  await api.delete(`/files/${fileId}`);
}; 