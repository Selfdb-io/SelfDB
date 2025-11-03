import React, { useState, useCallback } from 'react';
import { Button } from '../../../../components/ui/button';
import { ConfirmationDialog } from '../../../../components/ui/confirmation-dialog';
import { FileItem, deleteFile, downloadFile, uploadFile } from '../../../../services/fileService';
import { Download, Trash2, FileText, AlertCircle } from 'lucide-react';
import { Table, TableHeader } from '../../../../components/ui/table';
import { Pagination } from '../../../../components/ui/pagination';
import { useDropzone } from 'react-dropzone';

interface FileListProps {
  bucketId: string;
  files: FileItem[];
  onFileDeleted: (fileId: string) => void;
  loading: boolean;
  error: string | null;
  currentPage?: number;
  pageSize?: number;
  totalFiles?: number;
  totalPages?: number;
  onPageChange?: (page: number) => void;
  onUploadComplete?: (file: any) => void;
}

// Create an interface for the formatted file data
interface FormattedFileData extends Omit<FileItem, 'size' | 'created_at'> {
  size: string;
  created_at: string;
  content_type: string;
  rowNumber?: React.ReactNode;
}

const FileList: React.FC<FileListProps> = ({ bucketId, files, onFileDeleted, loading, error, currentPage = 1, pageSize = 100, totalFiles = 0, totalPages = 0, onPageChange, onUploadComplete }) => {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [fileToDelete, setFileToDelete] = useState<FileItem | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [downloadingFile, setDownloadingFile] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<{ fileId: string; message: string } | null>(null);
  const [dndUploading, setDndUploading] = useState(false);
  const [dndError, setDndError] = useState<string | null>(null);

  const processFiles = useCallback(async (filesToUpload: File[]) => {
    if (!filesToUpload || filesToUpload.length === 0) return;
    try {
      setDndUploading(true);
      setDndError(null);
      for (const file of filesToUpload) {
        await uploadFile(file, bucketId);
      }
      if (onUploadComplete) onUploadComplete(null);
    } catch (err: any) {
      console.error('Drag-and-drop upload failed:', err);
      setDndError(err?.message || 'Upload failed');
    } finally {
      setDndUploading(false);
    }
  }, [bucketId, onUploadComplete]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    await processFiles(acceptedFiles);
  }, [processFiles]);

  // Separate dropzones for empty state and non-empty list to ensure proper event capture
  const {
    getRootProps: getEmptyRootProps,
    getInputProps: getEmptyInputProps,
    isDragActive: isEmptyDragActive,
  } = useDropzone({ onDrop, multiple: true, noClick: true, noKeyboard: true });

  const {
    getRootProps: getListRootProps,
    getInputProps: getListInputProps,
    isDragActive: isListDragActive,
  } = useDropzone({ onDrop, multiple: true, noClick: true, noKeyboard: true });

  const handleDownload = async (fileId: string) => {
    try {
      // Add a loading state for the specific file being downloaded
      setDownloadingFile(fileId);
      
      // Get direct download URL and let browser handle streaming download immediately
      const downloadUrl = await downloadFile(bucketId, fileId);
      
      // Create a hidden anchor element
      const link = document.createElement('a');
      
      // Find the file to get its filename
      const file = files.find(f => f.id === fileId);
      if (!file) {
        throw new Error("File not found in the list");
      }
      
      // Set link properties
      link.href = downloadUrl;
      link.download = file.filename; // Set the download filename
      link.style.display = 'none';
      
      // Append to the document, trigger click, and remove
      document.body.appendChild(link);
      link.click();
      
      // Clean up by removing the element
      setTimeout(() => {
        document.body.removeChild(link);
      }, 100);
    } catch (err: any) {
      console.error('Error downloading file:', err);
      // Show error message to user
      const errorMessage = err.message || 'Failed to download file';
      setDownloadError({ fileId, message: errorMessage });
      
      // Clear error after a few seconds
      setTimeout(() => {
        setDownloadError(null);
      }, 5000);
    } finally {
      // Reset loading state quickly; download proceeds in browser
      setDownloadingFile(null);
    }
  };

  const handleDeleteClick = (file: FileItem) => {
    setFileToDelete(file);
    setDeleteDialogOpen(true);
    setDeleteError(null);
  };

  const handleDeleteConfirm = async () => {
    if (!fileToDelete) return;
    
    setDeleting(true);
    setDeleteError(null);
    
    try {
      await deleteFile(bucketId, fileToDelete.id);
      
      // Notify parent component
      if (onFileDeleted) {
        onFileDeleted(fileToDelete.id);
      }
      
      setDeleteDialogOpen(false);
    } catch (err: any) {
      setDeleteError(err.response?.data?.detail || 'Failed to delete file');
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setFileToDelete(null);
    setDeleteError(null);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const formatDate = (input: string) => {
    if (!input) return '-';
    const n = Number(input);
    const ms = Number.isFinite(n) ? (n < 1e12 ? n * 1000 : n) : Date.parse(input);
    const d = new Date(ms);
    return isNaN(d.getTime()) ? '-' : d.toLocaleString();
  };

  // Define table headers with row number as first column
  const tableHeaders: TableHeader[] = [
    { key: 'rowNumber', label: '#', isNumeric: true },
    { key: 'filename', label: 'Filename' },
    { key: 'content_type', label: 'Type' },
    { key: 'size', label: 'Size', isNumeric: true },
    { key: 'created_at', label: 'Uploaded' },
  ];

  // Format file data for the reusable Table component with row numbers
  const formattedData: FormattedFileData[] = files.map((file, index) => {
    // Calculate row number accounting for pagination
    const rowNumber = (currentPage - 1) * pageSize + index + 1;
    
    return {
      ...file,
      rowNumber: (
        <span className="font-mono text-secondary-600 dark:text-secondary-400">
          {rowNumber}
        </span>
      ),
      size: formatFileSize(file.size),
      created_at: formatDate(file.created_at),
      content_type: file.content_type || 'Unknown'
    };
  });

  // Render row icon
  const renderRowIcon = () => <FileText className="h-5 w-5 text-primary-600" />;

  // Render action buttons
  const renderActions = (item: FormattedFileData) => {
    // Get the original file from ID
    const originalFile = files.find(f => f.id === item.id);
    if (!originalFile) return null;
    
    const isDownloading = downloadingFile === item.id;
    const hasDownloadError = downloadError?.fileId === item.id;
    
    return (
      <>
        {/* Download button with loading state */}
        <Button
          variant="outline"
          size="sm"
          className={`mr-2 flex items-center ${hasDownloadError ? 'border-error-300 dark:border-error-500 text-error-600 dark:text-error-400' : ''}`}
          onClick={() => handleDownload(item.id)}
          disabled={isDownloading}
        >
          {isDownloading ? (
            <span className="h-4 w-4 animate-spin rounded-full border-b-2 border-current mr-1" />
          ) : (
            <Download className="w-4 h-4" />
          )}
          {hasDownloadError ? 'Retry' : ''}
        </Button>
        
        <Button
          variant="outline"
          size="sm"
          className="text-error-600 dark:text-error-400 border-error-300 dark:border-error-500 hover:bg-error-50 dark:hover:bg-error-900/30 flex items-center"
          onClick={() => handleDeleteClick(originalFile)}
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </>
    );
  };

  // Empty state content
  const EmptyState = () => (
    <div className="bg-white dark:bg-secondary-800 p-8 text-center rounded-lg shadow border border-secondary-200 dark:border-secondary-700">
      <FileText className="h-16 w-16 mx-auto text-secondary-400 mb-4" />
      <h3 className="text-lg font-heading font-semibold text-secondary-800 dark:text-secondary-300">
        No files uploaded yet
      </h3>
      <p className="mt-2 text-secondary-600 dark:text-secondary-400">
        Click Upload above or drag files here to upload
      </p>
    </div>
  );



  return (
    <>
      {downloadError && (
        <div className="mb-4 text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30 p-4 rounded text-sm flex items-start">
          <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" />
          <div>Download failed: {downloadError.message}</div>
        </div>
      )}
      {dndError && (
        <div className="mb-4 text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30 p-3 rounded text-sm">
          {dndError}
        </div>
      )}

      {files.length === 0 && !loading && !error ? (
        <div
          {...getEmptyRootProps()}
          className={`relative rounded-md ${isEmptyDragActive ? 'ring-2 ring-primary-500 ring-offset-2 ring-offset-transparent' : ''}`}
        >
          <input {...getEmptyInputProps()} />
          <EmptyState />
          {dndUploading && (
            <div className="mt-2 text-secondary-600 dark:text-secondary-300 text-sm text-center">Uploading...</div>
          )}
          {/* Full overlay to force-capture drop in empty state and prevent browser navigation */}
          <div
            className="absolute inset-0"
            onDragOver={(e) => {
              e.preventDefault();
              e.stopPropagation();
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              const fl = Array.from(e.dataTransfer?.files || []);
              if (fl.length) {
                processFiles(fl as File[]);
              }
            }}
          />
        </div>
      ) : (
        <div
          {...getListRootProps()}
          className={`rounded-md ${isListDragActive ? 'ring-2 ring-primary-500 ring-offset-2 ring-offset-transparent' : ''}`}
        >
          <input {...getListInputProps()} />
          <Table
            headers={tableHeaders}
            data={formattedData}
            isLoading={loading}
            errorMessage={error}
            renderRowIcon={renderRowIcon}
            renderActions={renderActions}
            containerClassName={`mt-4 ${isListDragActive ? 'bg-secondary-50 dark:bg-secondary-900/30' : ''}`}
          />

          {dndUploading && (
            <div className="mt-2 text-secondary-600 dark:text-secondary-300 text-sm">Uploading...</div>
          )}

          {/* Pagination Controls */}
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            totalItems={totalFiles}
            pageSize={pageSize}
            onPageChange={onPageChange || (() => {})}
            itemName="files"
          />
        </div>
      )}
      
      {/* Delete Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={deleteDialogOpen}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Confirm Delete"
        description={
          <>
            <p className="text-secondary-600 dark:text-secondary-300">
              Are you sure you want to delete the file "{fileToDelete?.filename}"? This action cannot be undone.
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
    </>
  );
};

export default FileList; 