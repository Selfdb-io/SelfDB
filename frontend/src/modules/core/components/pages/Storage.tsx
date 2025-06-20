import React, { useState, useEffect } from 'react';
import { PlusCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getUserBuckets, Bucket } from '../../../../services/bucketService';
import { BucketList, BucketForm } from '../storage';
import { Button } from '../../../../components/ui/button';
import realtimeService from '../../../../services/realtimeService';

const Storage: React.FC = () => {
  const [buckets, setBuckets] = useState<Bucket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editBucket, setEditBucket] = useState<Bucket | null>(null);
  const [formModalOpen, setFormModalOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchBuckets();
    
    // Use correct channel name with _changes suffix
    const bucketSubscriptionId = 'buckets_changes';
    realtimeService.subscribe(bucketSubscriptionId);
    
    // Also subscribe to file changes to update bucket sizes when files are added/deleted
    const tableSubscriptionId = 'tables_changes';
    realtimeService.subscribe(tableSubscriptionId);
    
    const handleBucketUpdate = (data: any) => {
      console.log('Received bucket update via WebSocket:', data);
      fetchBuckets(); // Refetch buckets when an update is received
    };
    
    const handleTableUpdate = (data: any) => {
      // Only update if the change is for files table
      if (data.table === 'files') {
        console.log('File update detected, refreshing buckets');
        fetchBuckets(); // Update bucket sizes when files change
      }
    };
    
    const removeBucketListener = realtimeService.addListener(bucketSubscriptionId, handleBucketUpdate);
    const removeTableListener = realtimeService.addListener(tableSubscriptionId, handleTableUpdate);
    
    return () => {
      removeBucketListener();
      removeTableListener();
      realtimeService.unsubscribe(bucketSubscriptionId);
      realtimeService.unsubscribe(tableSubscriptionId);
    };
  }, []);

  const fetchBuckets = async () => {
    try {
      setLoading(true);
      const data = await getUserBuckets();
      setBuckets(data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load buckets');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSuccess = (bucket: Bucket) => {
    setBuckets(prevBuckets => [...prevBuckets, bucket]);
  };

  const handleEditSuccess = (bucket: Bucket) => {
    setBuckets(prevBuckets => 
      prevBuckets.map(b => b.id === bucket.id ? bucket : b)
    );
  };

  const handleDeleteSuccess = (bucketId: string) => {
    setBuckets(prevBuckets => prevBuckets.filter(b => b.id !== bucketId));
  };

  const handleEditBucket = (bucket: Bucket) => {
    setEditBucket(bucket);
    setFormModalOpen(true);
  };

  const handleBucketClick = (bucketId: string) => {
    navigate(`/storage/${bucketId}`);
  };

  const handleCloseModal = () => {
    setFormModalOpen(false);
    setEditBucket(null);
  };

  const handleOpenCreateModal = () => {
    setEditBucket(null);
    setFormModalOpen(true);
  };

  return (
    <div className="p-2">
        <div className="flex justify-end mb-4">
          <Button 
            onClick={handleOpenCreateModal}
          >
            <PlusCircle className="mr-2 h-5 w-5" />
            Create Bucket
          </Button>
        </div>
     
      
      <div >
        {loading ? (
          <div className="flex justify-center items-center p-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : error ? (
          <div className="p-6 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg text-error-700 dark:text-error-300">
            <h3 className="text-lg font-heading font-semibold mb-2">Error Loading Buckets</h3>
            <p>{error}</p>
          </div>
        ) : (
          <BucketList 
            buckets={buckets}
            onBucketDeleted={handleDeleteSuccess}
            onEditBucket={handleEditBucket}
            onBucketClick={handleBucketClick}
            loading={false}
            error={null}
          />
        )}
      </div>

      {/* Bucket Form Modal */}
      <BucketForm
        isOpen={formModalOpen}
        onClose={handleCloseModal}
        onSuccess={editBucket ? handleEditSuccess : handleCreateSuccess}
        editBucket={editBucket}
      />
    </div>
  );
};

export default Storage;  