import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getTable, Table as TableType, deleteTable } from '../../../../services/tableService';
import { Loader } from '../ui/Loader';
import TableStructure from './TableStructure';
import TableData from './TableData';
import TableSql from './TableSql';
import TableRelationships from './TableRelationships';
import TableIndexes from './TableIndexes';
import { Pencil, Trash2, ChevronRight } from 'lucide-react';
import TableInfoModal from './TableInfoModal';
import { ConfirmationDialog } from '../../../../components/ui/confirmation-dialog';
import realtimeService from '../../../../services/realtimeService';

// TabPanel component for better tab management
interface TabPanelProps {
  children: React.ReactNode;
  activeTab: number;
  index: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, activeTab, index }) => {
  return (
    <div role="tabpanel" hidden={activeTab !== index} id={`table-tabpanel-${index}`}>
      {activeTab === index && children}
    </div>
  );
};

const TableDetail: React.FC = () => {
  const { tableName } = useParams<{ tableName: string }>();
  const navigate = useNavigate();
  const [tableInfo, setTableInfo] = useState<TableType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<number>(0);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  // Removed unused state variables for simplified table deletion
  const [isTableInfoModalOpen, setIsTableInfoModalOpen] = useState(false);
  // Add reference to the TableData component
  const tableDataRef = React.useRef<any>(null);

  useEffect(() => {
    const fetchTableDetails = async () => {
      if (!tableName) return;
      try {
        setLoading(true);
        // Fetch table metadata
        const tableData = await getTable(tableName);
        setTableInfo(tableData);
        setError(null);
      } catch (err: any) {
        console.error('Error fetching table details:', err);
        setError(err.response?.data?.detail || err.message || 'Failed to load table details');
      } finally {
        setLoading(false);
      }
    };

    fetchTableDetails();

    // Foreign key reference check removed as we're using CASCADE deletion

    // --- Real-time subscription for specific table updates ---
    if (!tableName) return;
    const subscriptionId = `${tableName}_changes`;
    // Subscribe to specific table changes
    realtimeService.subscribe(subscriptionId);

    // Listener for table updates
    const handleTableUpdate = (data: any) => {
      console.log('Received table update via WebSocket:', data);
      
      // If the operation is DELETE and it's for the current table, navigate back to tables list
      if (data.operation === 'DELETE' && data.table === tableName) {
        console.log('Current table was deleted, navigating back to tables list');
        // Unsubscribe from this table's notifications before navigating away
        if (subscriptionId) {
          realtimeService.unsubscribe(subscriptionId);
        }
        navigate('/tables');
        return;
      }
      
      // Update table metadata for other operations
      fetchTableDetails();
      
      // If we have data changes, trigger the TableData component to refresh
      if (data.operation && ['INSERT', 'UPDATE'].includes(data.operation)) {
        // Use the tableDataRef to access the refresh method if available
        if (tableDataRef.current && typeof tableDataRef.current.refreshData === 'function') {
          console.log('Refreshing table data due to realtime update');
          tableDataRef.current.refreshData();
        }
      }
    };
    const removeListener = realtimeService.addListener(subscriptionId, handleTableUpdate);

    return () => {
      removeListener();
      realtimeService.unsubscribe(subscriptionId);
    };
  }, [tableName]);

  const handleTabChange = (tabIndex: number) => {
    setActiveTab(tabIndex);
  };

  const handleDeleteClick = () => {
    setDeleteDialogOpen(true);
    setDeleteError(null);
  };

  const handleDeleteConfirm = async () => {
    if (!tableName) return;

    setDeleting(true);
    setDeleteError(null);

    try {
      await deleteTable(tableName);
      // Navigate back to tables list after successful deletion
      navigate('/tables');
    } catch (err: any) {
      console.error('Error deleting table:', err);
      setDeleteError(err.response?.data?.detail || err.message || 'Failed to delete table');
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setDeleteError(null);
  };

  const handleTableInfoUpdate = () => {
    // Refresh table data after update
    if (tableName) {
      getTable(tableName)
        .then(tableData => {
          setTableInfo(tableData);
        })
        .catch(err => {
          console.error('Error refreshing table details:', err);
        });
    }
  };

  if (loading) {
    return (
      <div className="p-2 ">
        <div className="flex items-center mb-4">
          <button
            onClick={() => navigate('/tables')}
            className="mr-4 text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 font-medium"
          >
            ← Back to Tables
          </button>
          <h2 className="text-2xl font-heading font-semibold text-secondary-800 dark:text-white tracking-tight">
            {tableName}
          </h2>
        </div>
        <div className="bg-white dark:bg-secondary-800 p-12 rounded-lg shadow border border-secondary-200 dark:border-secondary-700 flex justify-center">
          <Loader size="large" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-2">
        <div className="flex items-center mb-4">
          <button
            onClick={() => navigate('/tables')}
            className="mr-4 text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 font-medium"
          >
            ← Back to Tables
          </button>
          <h2 className="text-2xl font-heading font-semibold text-secondary-800 dark:text-white tracking-tight">
            Error Loading Table
          </h2>
        </div>
        <div className="bg-error-50 dark:bg-error-900/20 p-6 rounded-lg border border-error-200 dark:border-error-800 text-error-700 dark:text-error-300">
          <h3 className="text-lg font-heading font-semibold mb-2">Error</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  // Only proceed if we have a valid table name
  if (!tableName) {
    return (
      <div className="p-2">
        <div className="bg-error-50 dark:bg-error-900/20 p-6 rounded-lg border border-error-200 dark:border-error-800 text-error-700 dark:text-error-300">
          <h3 className="text-lg font-heading font-semibold mb-2">Error</h3>
          <p>Table name is not specified</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-2">
      {/* Breadcrumbs */}
      <nav className="flex items-center text-sm text-secondary-500 dark:text-secondary-400 mb-4">
        <Link to="/tables" className="hover:text-primary-600 dark:hover:text-primary-400">
          Tables
        </Link>
        <ChevronRight className="w-4 h-4 mx-2" />
        <span className="text-secondary-800 dark:text-white">{tableName}</span>
      </nav>
      
      <div className="flex items-center mb-4">
        <div className="flex items-baseline flex-1 mr-4"> 
          <h2 className="text-2xl font-heading font-semibold text-secondary-800 dark:text-white tracking-tight">
            {tableName}
          </h2>
          <div className="flex items-center ml-3">
            {tableInfo && tableInfo.description && (
              <span className="italic text-sm text-secondary-600 dark:text-secondary-400">
                {tableInfo.description}
              </span>
            )}
            <button
              onClick={() => setIsTableInfoModalOpen(true)}
              className="ml-2 p-1 text-secondary-400 hover:text-secondary-600 dark:hover:text-secondary-300 transition-colors"
              title="Edit table info"
            >
              <Pencil className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div>
          <button
            onClick={handleDeleteClick}
            className="p-2 rounded-md text-error-600 dark:text-error-400 border border-error-300 dark:border-error-500 hover:bg-error-50 dark:hover:bg-error-900/30 transition-colors"
            aria-label="Delete table"
          >
            <Trash2 className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="mb-6 border-b border-secondary-200 dark:border-secondary-700">
        <div className="flex space-x-1 overflow-x-auto">
          <button
            onClick={() => handleTabChange(0)}
            className={`px-4 py-2 font-medium text-sm focus:outline-none ${
              activeTab === 0
                ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
                : 'text-secondary-600 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-300'
            }`}
            aria-controls={`table-tabpanel-0`}
            id={`table-tab-0`}
          >
            Data
          </button>
          <button
            onClick={() => handleTabChange(1)}
            className={`px-4 py-2 font-medium text-sm focus:outline-none ${
              activeTab === 1
                ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
                : 'text-secondary-600 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-300'
            }`}
            aria-controls={`table-tabpanel-1`}
            id={`table-tab-1`}
          >
            Structure
          </button>
          <button
            onClick={() => handleTabChange(2)}
            className={`px-4 py-2 font-medium text-sm focus:outline-none ${
              activeTab === 2
                ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
                : 'text-secondary-600 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-300'
            }`}
            aria-controls={`table-tabpanel-2`}
            id={`table-tab-2`}
          >
            SQL
          </button>
          <button
            onClick={() => handleTabChange(3)}
            className={`px-4 py-2 font-medium text-sm focus:outline-none ${
              activeTab === 3
                ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
                : 'text-secondary-600 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-300'
            }`}
            aria-controls={`table-tabpanel-3`}
            id={`table-tab-3`}
          >
            Relationships
          </button>
          <button
            onClick={() => handleTabChange(4)}
            className={`px-4 py-2 font-medium text-sm focus:outline-none ${
              activeTab === 4
                ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
                : 'text-secondary-600 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-300'
            }`}
            aria-controls={`table-tabpanel-4`}
            id={`table-tab-4`}
          >
            Indexes
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div>
        <TabPanel activeTab={activeTab} index={0}>
          <TableData 
            ref={tableDataRef}
            tableName={tableName} 
          />
        </TabPanel>

        <TabPanel activeTab={activeTab} index={1}>
          {tableInfo && tableInfo.columns && (
            <TableStructure 
              columns={tableInfo.columns} 
              primaryKeys={tableInfo.primary_keys || []}
              tableName={tableName}
              tableDescription={tableInfo.description}
              onStructureChange={() => {
                // Refresh table data when structure changes
                if (tableName) {
                  getTable(tableName)
                    .then(tableData => {
                      setTableInfo(tableData);
                    })
                    .catch(err => {
                      console.error('Error refreshing table details:', err);
                    });
                }
              }}
            />
          )}
        </TabPanel>

        <TabPanel activeTab={activeTab} index={2}>
          <TableSql tableName={tableName} />
        </TabPanel>

        <TabPanel activeTab={activeTab} index={3}>
          {tableInfo && (
            <TableRelationships 
              tableName={tableName}
              foreignKeys={tableInfo.foreign_keys || []} 
            />
          )}
        </TabPanel>

        <TabPanel activeTab={activeTab} index={4}>
          {tableInfo && (
            <TableIndexes 
              tableName={tableName}
              indexes={tableInfo.indexes || []} 
            />
          )}
        </TabPanel>
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={deleteDialogOpen}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Confirm Delete"
        description={
          <>
            <p className="text-sm text-secondary-500 dark:text-secondary-400">
              Are you sure you want to delete the table "{tableName}"? This will permanently delete the table and all its data. This action cannot be undone.
            </p>
            
            {deleteError && (
              <div className="mt-3 p-2 bg-error-100 dark:bg-error-900 text-error-700 dark:text-error-300 rounded-md text-sm">
                {deleteError}
              </div>
            )}
          </>
        }
        confirmButtonText={deleting ? "Deleting..." : "Delete"}
        isDestructive={true}
        isConfirmLoading={deleting}
      />

      {/* Table Info Modal */}
      {tableName && (
        <TableInfoModal
          isOpen={isTableInfoModalOpen}
          onClose={() => setIsTableInfoModalOpen(false)}
          tableName={tableName}
          tableDescription={tableInfo?.description || ''}
          onStructureChange={handleTableInfoUpdate}
        />
      )}
    </div>
  );
};

export default TableDetail;  