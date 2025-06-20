import React from 'react';
import { Bucket } from '../../../../services/bucketService';
import { Folder, MoreVertical } from 'lucide-react';
import { Table, TableHeader } from '../../../../components/ui/table';

interface BucketListProps {
  buckets: Bucket[];
  onBucketDeleted: (bucketId: string) => void;
  onEditBucket: (bucket: Bucket) => void;
  onBucketClick: (bucketId: string) => void;
  loading: boolean;
  error: string | null;
}

// Create an interface for the formatted bucket data
interface FormattedBucketData extends Omit<Bucket, 'total_size'> {
  total_size: string;
  visibility: React.ReactNode;
}

const BucketList: React.FC<BucketListProps> = ({ 
  buckets, 
  onBucketClick,
  loading, 
  error 
}) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Define table headers
  const tableHeaders: TableHeader[] = [
    { key: 'name', label: 'Name' },
    { key: 'description', label: 'Description' },
    { key: 'file_count', label: 'Files', isNumeric: true },
    { key: 'total_size', label: 'Size', isNumeric: true },
    { key: 'visibility', label: 'Visibility' },
    { key: 'created_at', label: 'Created' },
  ];

  // Format bucket data for the reusable Table component
  const formattedData: FormattedBucketData[] = buckets.map(bucket => ({
    ...bucket,
    total_size: formatSize(bucket.total_size),
    visibility: (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        bucket.is_public 
          ? 'bg-success-100 dark:bg-success-900 text-success-800 dark:text-success-100' 
          : 'bg-secondary-100 dark:bg-secondary-700 text-secondary-800 dark:text-secondary-100'
      }`}>
        {bucket.is_public ? 'Public' : 'Private'}
      </span>
    ),
    created_at: formatDate(bucket.created_at)
  }));

  // Render row icon
  const renderRowIcon = () => <Folder className="h-5 w-5 text-primary-600" />;

  // Render action buttons
  const renderActions = (item: FormattedBucketData) => {
    return (
      <button
        onClick={(e) => {
          e.stopPropagation();
          onBucketClick(item.id);
        }}
        className="text-secondary-600 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-300"
        aria-label="View bucket details"
      >
        <MoreVertical className="h-5 w-5" />
      </button>
    );
  };

  // Handle row click
  const handleRowClick = (item: FormattedBucketData) => {
    onBucketClick(item.id);
  };

  // Empty state content
  const EmptyState = () => (
    <div className="bg-white dark:bg-secondary-800 p-8 text-center rounded-lg shadow border border-secondary-200 dark:border-secondary-700">
      <Folder className="h-16 w-16 mx-auto text-secondary-400 mb-4" />
      <h3 className="text-lg font-heading font-semibold text-secondary-800 dark:text-secondary-300">
        No buckets created yet
      </h3>
      <p className="mt-2 text-secondary-600 dark:text-secondary-400">
        Use the form above to create your first storage bucket
      </p>
    </div>
  );

  return (
    <>
      {buckets.length === 0 && !loading && !error ? (
        <EmptyState />
      ) : (
        <div>    
          <Table
            headers={tableHeaders}
            data={formattedData}
            isLoading={loading}
            errorMessage={error}
            renderRowIcon={renderRowIcon}
            renderActions={renderActions}
            onRowClick={handleRowClick}
            containerClassName="mt-4"
          />
        </div>
      )}
    </>
  );
};

export default BucketList; 