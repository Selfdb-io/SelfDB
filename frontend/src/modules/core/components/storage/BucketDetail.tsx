import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Bucket, getBucket, getBucketFiles, deleteBucketAndContents, updateBucket } from '../../../../services/bucketService'; // Updated import
import realtimeService from '../../../../services/realtimeService';
import { FileItem, uploadFile } from '../../../../services/fileService';
import { Button } from '../../../../components/ui/button';
import { ConfirmationDialog } from '../../../../components/ui/confirmation-dialog';
import { FileList, BucketFormModal, BucketInfoDisplay } from '.';
import { ArrowLeft, ChevronRight, Upload, Trash2, Pencil } from 'lucide-react';

const BucketDetail: React.FC = () => {
  const { bucketId } = useParams<{ bucketId: string }>();
  const navigate = useNavigate();
  const [bucket, setBucket] = useState<Bucket | null>(null);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isBucketInfoModalOpen, setIsBucketInfoModalOpen] = useState(false);
  
  // Add pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(100);
  const [totalFiles, setTotalFiles] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  useEffect(() => {
    if (bucketId) {
      fetchBucketDetails(bucketId);
      
      // Subscribe to real-time updates for both bucket changes and file changes
      const bucketSubscriptionId = 'buckets_events';
      const filesSubscriptionId = 'files_events';
      
      realtimeService.subscribe(bucketSubscriptionId);
      realtimeService.subscribe(filesSubscriptionId);
      
      // Handle bucket updates (metadata changes)
      const handleBucketUpdate = (data: any) => {
        console.log('Received bucket update via WebSocket:', data);
        if (data.operation === 'UPDATE' && data.data?.id === bucketId) {
          console.log('Updating bucket details');
          fetchBucketDetails(bucketId);
        }
      };
      
      // Handle file updates (new files, deleted files, updated files)
      const handleFileUpdate = (data: any) => {
        console.log('Received file update via WebSocket:', data);
        // Only refresh if the file change is for this bucket
        if (data.data?.bucket_id === bucketId) {
          console.log('Updating files for bucket', bucketId);
          // Reset to first page when files change to ensure we see new files
          setCurrentPage(1);
          fetchBucketDetails(bucketId);
        }
      };
      
      const removeBucketListener = realtimeService.addListener(bucketSubscriptionId, handleBucketUpdate);
      const removeFileListener = realtimeService.addListener(filesSubscriptionId, handleFileUpdate);
      
      return () => {
        // Clean up listeners and subscriptions
        removeBucketListener();
        removeFileListener();
        realtimeService.unsubscribe(bucketSubscriptionId);
        realtimeService.unsubscribe(filesSubscriptionId);
      };
    }
  }, [bucketId, currentPage]); // Add currentPage to dependency array

  const fetchBucketDetails = async (id: string) => {
    try {
      setLoading(true);
      // Fetch bucket details
      const bucketData = await getBucket(id);
      
      // Fetch files in this bucket with pagination
      const skip = (currentPage - 1) * pageSize;
      const filesData = await getBucketFiles(id, { skip, limit: pageSize });
      
      // Convert BucketFile to FileItem
      const fileItems: FileItem[] = filesData.map(file => ({
        ...file,
        bucket_id: id
      }));
      setFiles(fileItems);
      
      // Compute counts and total size from files
      const computedFileCount = fileItems.length;
      const computedTotalSize = fileItems.reduce((sum, f) => sum + (f.size || 0), 0);
      
      // Update bucket with computed metrics
      setBucket({
        ...bucketData,
        file_count: computedFileCount,
        total_size: computedTotalSize,
      });
      
      // Set total files and pages based on computed file count
      setTotalFiles(computedFileCount);
      setTotalPages(Math.ceil(computedFileCount / pageSize));
      
      setError(null);
    } catch (err: any) {
      console.error('Error fetching bucket details:', err);
      const status = err?.response?.status;
      if (status === 404) {
        navigate('/storage');
        return;
      }
      setError('Failed to load bucket details. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteClick = () => {
    setDeleteDialogOpen(true);
    setDeleteError(null);
  };

  const handleDeleteConfirm = async () => {
    if (!bucketId) return;
    
    setDeleting(true);
    setDeleteError(null);
    
    try {
      await deleteBucketAndContents(bucketId); // Updated function call
      // Navigate back to storage page
      navigate('/storage');
    } catch (err: any) {
      setDeleteError(err.response?.data?.detail || 'Failed to delete bucket and its contents'); // Updated error message
      setDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setDeleteError(null);
  };

  const handleUploadComplete = (_newFile: any) => {
    // Reset to first page to see the new file
    setCurrentPage(1);
    // Refresh bucket data to get updated counts and files
    if (bucketId) {
      fetchBucketDetails(bucketId);
    }
  };

  const handleFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!bucketId) return;
    const selectedFiles = e.target.files;
    if (!selectedFiles || selectedFiles.length === 0) return;
    try {
      setUploading(true);
      setUploadError(null);
      for (const file of Array.from(selectedFiles)) {
        await uploadFile(file, bucketId);
      }
      handleUploadComplete(null);
    } catch (err: any) {
      console.error('Upload failed:', err);
      setUploadError(err?.message || 'Upload failed');
    } finally {
      setUploading(false);
      // Reset the input so the same file can be selected again
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleFileDeleted = async (_fileId: string) => {
    try {
      // Just refresh the data to get updated counts and file list
      if (bucketId) {
        fetchBucketDetails(bucketId);
      }
    } catch (err) {
      console.error('Error deleting file:', err);
      setError('Failed to delete file. Please try again later.');
    }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleBucketInfoUpdate = async (updatedBucket: Partial<Bucket>) => {
    if (!bucketId || !bucket) return;

    try {
      await updateBucket(bucketId, updatedBucket);
      // Refresh bucket data
      fetchBucketDetails(bucketId);
    } catch (err: any) {
      console.error('Error updating bucket:', err);
      setError('Failed to update bucket. Please try again.');
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-48">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-2 space-y-4">
        <div className="text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30 p-4 rounded mb-4">
          {error}
        </div>
        <Button variant="outline" onClick={() => navigate('/storage')} className="flex items-center">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Buckets
        </Button>
      </div>
    );
  }

  if (!bucket || !bucketId) {
    return (
      <div className="p-2 space-y-4">
        <div className="text-warning-600 dark:text-warning-400 bg-warning-50 dark:bg-warning-900/30 p-4 rounded mb-4">
          Bucket not found or you don't have permission to access it.
        </div>
        <Button variant="outline" onClick={() => navigate('/storage')} className="flex items-center">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Buckets
        </Button>
      </div>
    );
  }

  return (
    <div className="p-2 space-y-6">
      {/* Breadcrumbs */}
      <nav className="flex items-center text-sm text-secondary-500 dark:text-secondary-400 mb-4">
        <Link to="/storage" className="hover:text-primary-600 dark:hover:text-primary-400">
          Buckets
        </Link>
        <ChevronRight className="w-4 h-4 mx-2" />
        <span className="text-secondary-800 dark:text-white">{bucket.name}</span>
      </nav>
      
      {/* Header - Updated to match TableDetail style */}
      <div className="flex items-center mb-4">
        <div className="flex items-baseline flex-1 mr-4"> 
          <h2 className="text-2xl font-heading font-semibold text-secondary-800 dark:text-white tracking-tight">
            {bucket.name}
          </h2>
          <div className="flex items-center ml-3">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              bucket.is_public 
                ? 'bg-success-100 dark:bg-success-900 text-success-800 dark:text-success-100' 
                : 'bg-secondary-100 dark:bg-secondary-700 text-secondary-800 dark:text-secondary-100'
            }`}>
              {bucket.is_public ? 'Public' : 'Private'}
            </span>
            {bucket.description && (
              <span className="ml-2 italic text-sm text-secondary-600 dark:text-secondary-400">
                {bucket.description}
              </span>
            )}
            <button
              onClick={() => setIsBucketInfoModalOpen(true)}
              className="ml-2 p-1 text-secondary-400 hover:text-secondary-600 dark:hover:text-secondary-300 transition-colors"
              title="Edit bucket info"
            >
              <Pencil className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div>
          <button
            onClick={handleDeleteClick}
            className="p-2 rounded-md text-error-600 dark:text-error-400 border border-error-300 dark:border-error-500 hover:bg-error-50 dark:hover:bg-error-900/30 transition-colors"
            aria-label="Delete bucket"
          >
            <Trash2 className="h-5 w-5" />
          </button>
        </div>
      </div>
      
      {/* Bucket Info Display */}
      <BucketInfoDisplay 
        fileCount={bucket.file_count}
        totalSize={formatSize(bucket.total_size)}
        createdAt={new Date(bucket.created_at).toLocaleDateString()}
      />
      
      {/* Upload Button + Hidden Input */}
      <div className="flex justify-end">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={handleFileInputChange}
        />
        <Button 
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center"
          disabled={uploading}
        >
          {uploading ? (
            <span className="mr-2 animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
          ) : (
            <Upload className="w-4 h-4 mr-2" />
          )}
          {uploading ? 'Uploading...' : 'Upload File to Bucket'}
        </Button>
      </div>
      {uploadError && (
        <div className="mt-2 text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30 p-2 rounded text-sm">
          {uploadError}
        </div>
      )}
      
      {/* File List */}
      <FileList 
        bucketId={bucketId}
        files={files} 
        onFileDeleted={handleFileDeleted} 
        loading={loading} 
        error={error}
        currentPage={currentPage}
        pageSize={pageSize}
        totalFiles={totalFiles}
        totalPages={totalPages}
        onPageChange={handlePageChange}
        onUploadComplete={handleUploadComplete}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={deleteDialogOpen}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Confirm Delete"
        description={
          <>
            <p className="text-secondary-600 dark:text-secondary-300">
              Are you sure you want to delete the bucket "{bucket?.name}"? This will permanently delete all files in this bucket. This action cannot be undone.
            </p>
            
            {deleteError && (
              <div className="text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30 p-4 rounded mt-4 text-sm">
                {deleteError}
              </div>
            )}
          </>
        }
        confirmButtonText={deleting ? "Deleting..." : "Delete"}
        isDestructive={true}
        isConfirmLoading={deleting}
      />

      {/* Bucket Info Modal */}
      {bucket && (
        <BucketFormModal
          isOpen={isBucketInfoModalOpen}
          onClose={() => setIsBucketInfoModalOpen(false)}
          onSubmit={handleBucketInfoUpdate}
          bucket={bucket}
          title="Edit Bucket"
          submitButtonText="Update Bucket"
        />
      )}
    </div>
  );
};

export default BucketDetail;