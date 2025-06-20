import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from '../../../../components/ui/button';
import { uploadFile } from '../../../../services/fileService';
import { Upload, FileText, AlertCircle } from 'lucide-react';

interface FileUploaderProps {
  onUploadComplete: (file: any) => void;
  bucketId: string;
}

const FileUploader: React.FC<FileUploaderProps> = ({ 
  onUploadComplete, 
  bucketId
}) => {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[], fileRejections: any[]) => {
    if (fileRejections.length > 0) {
      const rejection = fileRejections[0];
      setError(`File rejected: ${rejection.errors[0]?.message || 'Unknown error'}`);
      return;
    }
    
    setFiles(acceptedFiles);
    setError(null);
    setSuccess(false);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false, // Allow only one file at a time
  });

  const handleUpload = async () => {
    if (files.length === 0) return;

    setUploading(true);
    setUploadProgress(0);
    setError(null);
    setSuccess(false);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 95) {
            clearInterval(progressInterval);
            return 95;
          }
          return prev + 5;
        });
      }, 200);

      console.log(`Starting upload of ${files[0].name} to bucket ${bucketId}`);
      
      // Use the updated uploadFile function that handles the two-step process
      const result = await uploadFile(files[0], bucketId);

      clearInterval(progressInterval);
      setUploadProgress(100);
      setSuccess(true);
      setFiles([]);

      console.log('Upload completed successfully:', result);
      
      // Notify parent component
      if (onUploadComplete) {
        onUploadComplete(result);
      }
    } catch (err: any) {
      console.error("Upload error details:", err);

      // Extract more detailed error message if possible
      let errorMessage = '';
      
      if (err instanceof Error) {
        errorMessage = err.message;
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (typeof err === 'string') {
        errorMessage = err;
      } else {
        errorMessage = 'Unknown upload error occurred';
      }
      
      setError(errorMessage);
      
      // Reset progress
      setUploadProgress(0);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-white dark:bg-secondary-800 p-6 rounded-lg shadow border border-secondary-200 dark:border-secondary-700 mb-6">
      <h3 className="text-xl font-semibold text-secondary-800 dark:text-white mb-4">
        Upload File
      </h3>

      {error && (
        <div className="text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30 p-4 rounded mb-4 text-sm flex items-start">
          <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" />
          <div>{error}</div>
        </div>
      )}

      {success && (
        <div className="text-success-600 dark:text-success-400 bg-success-50 dark:bg-success-900/30 p-4 rounded mb-4 text-sm">
          File uploaded successfully!
        </div>
      )}

      <div
        {...getRootProps()}
        className={`border-2 border-dashed border-secondary-300 dark:border-secondary-600 rounded-lg p-6 text-center cursor-pointer mb-4 ${
          isDragActive 
            ? 'bg-secondary-50 dark:bg-secondary-800/50' 
            : 'hover:bg-secondary-50 dark:hover:bg-secondary-800/50'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="w-12 h-12 mx-auto text-primary-600 mb-3" />
        {isDragActive ? (
          <p className="text-secondary-600 dark:text-secondary-300">Drop the file here...</p>
        ) : (
          <div>
            <p className="text-secondary-600 dark:text-secondary-300">Drag and drop a file here, or click to select a file</p>
          </div>
        )}
      </div>

      {files.length > 0 && (
        <ul className="divide-y divide-secondary-200 dark:divide-secondary-700 mb-4">
          {files.map((file, index) => (
            <li key={index} className="py-3 flex items-center">
              <FileText className="w-5 h-5 text-primary-600 mr-3" />
              <div>
                <p className="text-secondary-800 dark:text-white text-sm font-medium">{file.name}</p>
                <p className="text-secondary-500 dark:text-secondary-400 text-xs">{(file.size / 1024).toFixed(2)} KB</p>
              </div>
            </li>
          ))}
        </ul>
      )}

      {uploading && (
        <div className="my-4">
          <div className="relative h-2 bg-secondary-200 dark:bg-secondary-700 rounded-full overflow-hidden">
            <div 
              className="bg-primary-600 h-full transition-all duration-300 ease-in-out"
              style={{ width: `${uploadProgress}%` }}
            ></div>
          </div>
          <p className="text-secondary-500 dark:text-secondary-400 text-sm text-center mt-2">
            {uploadProgress}%
          </p>
        </div>
      )}

      <Button
        onClick={handleUpload}
        disabled={files.length === 0 || uploading}
        className="mt-2"
      >
        {uploading ? (
          <>
            <span className="mr-2 animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
            Uploading...
          </>
        ) : 'Upload'}
      </Button>
    </div>
  );
};

export default FileUploader; 