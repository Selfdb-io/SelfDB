import React from 'react';

interface BucketInfoDisplayProps {
  fileCount: number;
  totalSize: string; // Expect pre-formatted size
  createdAt: string; // Expect pre-formatted date
}

const BucketInfoDisplay: React.FC<BucketInfoDisplayProps> = ({ 
  fileCount, 
  totalSize, 
  createdAt 
}) => {
  return (
    <div className="bg-white dark:bg-secondary-800 p-6 rounded-lg shadow border border-secondary-200 dark:border-secondary-700">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <p className="text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider mb-1">Files</p>
          <p className="text-secondary-500 dark:text-secondary-400 text-xs">{fileCount}</p>
        </div>
        <div>
          <p className="text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider mb-1">Total Size</p>
          <p className="text-secondary-500 dark:text-secondary-400 text-xs">{totalSize}</p>
        </div>
        <div>
          <p className="text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider mb-1">Created</p>
          <p className="text-secondary-500 dark:text-secondary-400 text-xs">{createdAt}</p>
        </div>
      </div>
    </div>
  );
};

export default BucketInfoDisplay; 