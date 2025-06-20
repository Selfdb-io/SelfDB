import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PlusCircle } from 'lucide-react';
import TableList from '../tables/TableList';
import TableCreate from '../tables/TableCreate';
import { Button } from '../../../../components/ui/button';
import { getTables, Table } from '../../../../services/tableService';
import realtimeService from '../../../../services/realtimeService';

const Tables: React.FC = () => {
  const [tables, setTables] = useState<Table[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const navigate = useNavigate();

  const fetchTables = async () => {
    try {
      setLoading(true);
      const data = await getTables();
      setTables(data);
      setError(null);
    } catch (err: any) {
      console.error('Error fetching tables:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load tables');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTables();
    
    // Use correct channel name with _changes suffix
    const subscriptionId = 'tables_changes';
    realtimeService.subscribe(subscriptionId);

    const handleTableUpdate = (data: any) => {
      console.log('Received table update via WebSocket:', data);
      fetchTables(); // Refetch tables when an update is received
    };

    const removeListener = realtimeService.addListener(subscriptionId, handleTableUpdate);

    return () => {
      removeListener();
      realtimeService.unsubscribe(subscriptionId);
    };
  }, []);

  const handleTableClick = (tableName: string) => {
    navigate(`/tables/${tableName}`);
  };

  const handleOpenCreateModal = () => {
    setCreateModalOpen(true);
  };

  const handleCloseCreateModal = () => {
    setCreateModalOpen(false);
  };

  return (
    <div className="p-2">
      <div className="flex justify-end mb-4">
        <Button
          onClick={handleOpenCreateModal}
          leftIcon={<PlusCircle className="h-5 w-5 mr-2" />}
        >
          Create New Table
        </Button>
      </div>

      <div className="bg-white dark:bg-secondary-800 rounded-lg shadow border border-secondary-200 dark:border-secondary-700">
        {loading ? (
          <div className="flex justify-center items-center p-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : error ? (
          <div className="p-6 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg text-error-700 dark:text-error-300">
            <h3 className="text-lg font-heading font-semibold mb-2">Error Loading Tables</h3>
            <p>{error}</p>
          </div>
        ) : (
          <TableList
            tables={tables}
            onTableClick={handleTableClick}
            onTableDeleted={(tableName) => {
              // Remove the deleted table from the list
              setTables(prevTables => prevTables.filter(table => table.name !== tableName));
            }}
          />
        )}
      </div>

      {/* Table Create Modal */}
      <TableCreate 
        isOpen={createModalOpen} 
        onClose={handleCloseCreateModal} 
        onTableCreated={fetchTables}
      />
    </div>
  );
};

export default Tables;  