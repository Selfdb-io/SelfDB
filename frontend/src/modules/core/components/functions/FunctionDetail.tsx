import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getFunction, deleteFunction, SelfFunction, getFunctionExecutions, FunctionExecution } from '../../../../services/functionService';
import { getWebhooks, Webhook, deleteWebhook } from '../../../../services/webhookService';
import { Loader } from '../ui/Loader';
import { ConfirmationDialog } from '../../../../components/ui/confirmation-dialog';
import { ChevronRight, Pencil, Trash2 } from 'lucide-react';
import CodeEditor from './CodeEditor';
import FunctionForm from './FunctionForm';
import WebhookList from '../webhooks/WebhookList';
import WebhookForm from '../webhooks/WebhookForm';
import WebhookDetail from '../webhooks/WebhookDetail';
import { Table } from '../../../../components/ui/table';
import { Pagination } from '../../../../components/ui/pagination';

// Removed Versions model – backend does not expose versions endpoint

// TabPanel component for better tab management
interface TabPanelProps {
  children: React.ReactNode;
  activeTab: number;
  index: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, activeTab, index }) => {
  return (
    <div role="tabpanel" hidden={activeTab !== index} id={`function-tabpanel-${index}`}>
      {activeTab === index && <div className="py-4">{children}</div>}
    </div>
  );
};

// Status toggle removed – backend doesn't support status mutations

const FunctionDetail: React.FC = () => {
  const { functionId } = useParams<{ functionId: string }>();
  const navigate = useNavigate();
  const [functionData, setFunctionData] = useState<SelfFunction | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isFunctionInfoModalOpen, setIsFunctionInfoModalOpen] = useState(false);
  
  // Webhooks state
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [webhooksLoading, setWebhooksLoading] = useState(false);
  const [webhooksError, setWebhooksError] = useState<string | null>(null);
  const [showWebhookForm, setShowWebhookForm] = useState(false);
  const [editingWebhook, setEditingWebhook] = useState<Webhook | null>(null);
  const [selectedWebhookId, setSelectedWebhookId] = useState<string | null>(null);
  const [deleteWebhookDialogOpen, setDeleteWebhookDialogOpen] = useState(false);
  const [isDeletingWebhook, setIsDeletingWebhook] = useState(false);
  const [deleteWebhookError, setDeleteWebhookError] = useState<string | null>(null);

  // Executions state
  const [executions, setExecutions] = useState<FunctionExecution[]>([]);
  const [executionsLoading, setExecutionsLoading] = useState(false);
  const [executionsError, setExecutionsError] = useState<string | null>(null);
  // Executions pagination state (we fetch 200 per page)
  const [execPage, setExecPage] = useState(1);
  const [execPageSize] = useState(200);
  const [execTotal, setExecTotal] = useState(0);
  const [execTotalPages, setExecTotalPages] = useState(0);

  const handleDeleteWebhookConfirm = async () => {
    if (!selectedWebhookId) return;
    setIsDeletingWebhook(true);
    setDeleteWebhookError(null);
    try {
      await deleteWebhook(selectedWebhookId);
      // remove from list and close detail
      setWebhooks(prev => prev.filter(w => w.id !== selectedWebhookId));
      setSelectedWebhookId(null);
      setDeleteWebhookDialogOpen(false);
    } catch (err: any) {
      console.error('Error deleting webhook:', err);
      setDeleteWebhookError(err.response?.data?.detail || err.message || 'Failed to delete webhook');
    } finally {
      setIsDeletingWebhook(false);
    }
  };

  useEffect(() => {
    if (!functionId) return;

    const fetchData = async () => {
      try {
        setLoading(true);
        // Fetch function details
        const data = await getFunction(functionId);
        setFunctionData(data);
        setError(null);
        
          // Fetch webhooks for this function
          await fetchWebhooks();
          // Fetch executions for this function (paged)
          await fetchExecutions();
      } catch (err: any) {
        console.error('Error fetching data:', err);
        setError(err.response?.data?.detail || err.message || 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [functionId, execPage]);

  const handleTabChange = (tabIndex: number) => {
    setActiveTab(tabIndex);
  };

  const handleDeleteClick = () => {
    setDeleteDialogOpen(true);
    setDeleteError(null);
  };

  const handleDeleteConfirm = async () => {
    if (!functionId) return;

    setIsDeleting(true);
    setDeleteError(null);

    try {
      await deleteFunction(functionId);
      // Navigate back to functions list after successful deletion
      navigate('/functions');
    } catch (err: any) {
      console.error('Error deleting function:', err);
      setDeleteError(err.response?.data?.detail || err.message || 'Failed to delete function');
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setDeleteError(null);
  };

  const handleFunctionInfoUpdate = () => {
    // Refresh function data after update
    if (functionId) {
      getFunction(functionId)
        .then(data => {
          setFunctionData(data);
        })
        .catch(err => {
          console.error('Error refreshing function data:', err);
        });
    }
  };

  // Webhooks functions
  const fetchWebhooks = async () => {
    if (!functionId) return;
    
    try {
      setWebhooksLoading(true);
      setWebhooksError(null);
      const response = await getWebhooks(100, 0); // Get all webhooks, we'll filter by function_id
      const functionWebhooks = response.webhooks.filter(w => w.function_id === functionId);
      setWebhooks(functionWebhooks);
    } catch (err: any) {
      console.error('Error fetching webhooks:', err);
      setWebhooksError(err.response?.data?.detail || err.message || 'Failed to load webhooks');
    } finally {
      setWebhooksLoading(false);
    }
  };

  // Executions functions
  const fetchExecutions = async () => {
    if (!functionId) return;

    try {
      setExecutionsLoading(true);
      setExecutionsError(null);
      // Fetch executions for the overview strip with pagination
      const response = await getFunctionExecutions(functionId, execPageSize, (execPage - 1) * execPageSize);
      setExecutions(response.executions || []);
      setExecTotal(response.total || 0);
      setExecTotalPages(Math.ceil((response.total || 0) / execPageSize));
    } catch (err: any) {
      console.error('Error fetching executions:', err);
      setExecutionsError(err.response?.data?.detail || err.message || 'Failed to load executions');
    } finally {
      setExecutionsLoading(false);
    }
  };

  const handleCreateWebhook = () => {
    setEditingWebhook(null);
    setShowWebhookForm(true);
  };

  const handleEditWebhook = (webhook: Webhook) => {
    setEditingWebhook(webhook);
    setShowWebhookForm(true);
  };

  const handleWebhookFormClose = () => {
    setShowWebhookForm(false);
    setEditingWebhook(null);
  };

  const handleWebhookDeleted = (webhookId: string) => {
    setWebhooks(prev => prev.filter(w => w.id !== webhookId));
  };

  const handleWebhookUpdated = () => {
    fetchWebhooks(); // Refresh webhooks list
  };

  // Note: executions are fetched by the main fetchData flow and when execPage changes

  if (loading) {
    return (
      <div className="p-2">
        <div className="flex items-center mb-4">
          <button
            onClick={() => navigate('/functions')}
            className="mr-4 text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 font-medium"
          >
            ← Back to Functions
          </button>
          <h2 className="text-2xl font-heading font-semibold text-secondary-800 dark:text-white tracking-tight">
            Loading Function
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
            onClick={() => navigate('/functions')}
            className="mr-4 text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 font-medium"
          >
            ← Back to Functions
          </button>
          <h2 className="text-2xl font-heading font-semibold text-secondary-800 dark:text-white tracking-tight">
            Error Loading Function
          </h2>
        </div>
        <div className="bg-error-50 dark:bg-error-900/20 p-6 rounded-lg border border-error-200 dark:border-error-800 text-error-700 dark:text-error-300">
          <h3 className="text-lg font-heading font-semibold mb-2">Error</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!functionData || !functionId) {
    return (
      <div className="p-2">
        <div className="bg-error-50 dark:bg-error-900/20 p-6 rounded-lg border border-error-200 dark:border-error-800 text-error-700 dark:text-error-300">
          <h3 className="text-lg font-heading font-semibold mb-2">Error</h3>
          <p>Function not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-2">
      {/* Breadcrumbs */}
      <nav className="flex items-center text-sm text-secondary-500 dark:text-secondary-400 mb-4">
        <Link to="/functions" className="hover:text-primary-600 dark:hover:text-primary-400">
          Functions
        </Link>
        <ChevronRight className="w-4 h-4 mx-2" />
        <span className="text-secondary-800 dark:text-white">{functionData.name}</span>
      </nav>

      {/* Header */}
      <div className="flex items-center mb-4">
        <div className="flex items-baseline flex-1 mr-4">
          <h2 className="text-2xl font-heading font-semibold text-secondary-800 dark:text-white tracking-tight">
            {functionData.name}
          </h2>
          <div className="flex items-center ml-3">
            {functionData.description && (
              <span className="ml-2 italic text-sm text-secondary-600 dark:text-secondary-400">
                {functionData.description}
              </span>
            )}
            <button
              onClick={() => setIsFunctionInfoModalOpen(true)}
              className="ml-2 p-1 text-secondary-400 hover:text-secondary-600 dark:hover:text-secondary-300 transition-colors"
              title="Edit function information"
            >
              <Pencil className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={handleDeleteClick}
            className="p-2 rounded-md text-error-600 dark:text-error-400 border border-error-300 dark:border-error-500 hover:bg-error-50 dark:hover:bg-error-900/30 transition-colors"
            aria-label="Delete function"
            title="Delete function"
          >
            <Trash2 className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Tab Navigation (Overview, Code, Webhooks) */}
      <div className="mb-6 border-b border-secondary-200 dark:border-secondary-700">
        <div className="flex space-x-1 overflow-x-auto">
          <button
            onClick={() => handleTabChange(0)}
            className={`px-4 py-2 font-medium text-sm focus:outline-none ${
              activeTab === 0
                ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
                : 'text-secondary-600 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-300'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => handleTabChange(1)}
            className={`px-4 py-2 font-medium text-sm focus:outline-none ${
              activeTab === 1
                ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
                : 'text-secondary-600 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-300'
            }`}
          >
            Code
          </button>
          <button
            onClick={() => handleTabChange(2)}
            className={`px-4 py-2 font-medium text-sm focus:outline-none ${
              activeTab === 2
                ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
                : 'text-secondary-600 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-300'
            }`}
          >
            Webhooks
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="bg-white dark:bg-secondary-800 rounded-lg shadow border border-secondary-200 dark:border-secondary-700">
        <TabPanel activeTab={activeTab} index={0}>
          <div className="p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-secondary-800 dark:text-white">Function Executions</h3>
              <button
                onClick={() => setIsFunctionInfoModalOpen(true)}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
              >
                View Function Details
              </button>
            </div>

            {/* Execution status strip: fixed-width grid with 200 bars (green=success, red=failure, gray=empty) */}
            <div className="mb-4">
              <div className="w-full">
                <div
                  className="w-full"
                  style={{
                    display: 'grid',
                    gridTemplateColumns: `repeat(${execPageSize}, 1fr)`,
                    alignItems: 'center'
                  }}
                >
                  {Array.from({ length: execPageSize }).map((_, slotIndex) => {
                    const ex = executions[slotIndex];
                    if (ex) {
                      let isSuccess = false;
                      try {
                        if (ex.result) {
                          const parsed = typeof ex.result === 'string' ? (() => { try { return JSON.parse(ex.result); } catch { return null; } })() : ex.result;
                          if (parsed && typeof parsed === 'object' && 'success' in parsed) {
                            isSuccess = !!parsed.success;
                          } else {
                            isSuccess = ex.status === 'completed';
                          }
                        } else {
                          isSuccess = ex.status === 'completed';
                        }
                      } catch (e) {
                        isSuccess = ex.status === 'completed';
                      }

                      return (
                        <div
                          key={ex.id || slotIndex}
                          title={`${ex.started_at || ex.created_at || ''} — ${isSuccess ? 'success' : 'failure'}`}
                          className={`rounded-sm ${isSuccess ? 'bg-success-500 dark:bg-success-400' : 'bg-error-500 dark:bg-error-400'}`}
                          style={{ width: '50%', height: '20px', justifySelf: 'center' }}
                        />
                      );
                    }

                    // empty slot
                    return (
                      <div
                        key={`empty-${slotIndex}`}
                        title={`No execution`}
                        className="rounded-sm bg-secondary-200 dark:bg-secondary-700"
                        style={{ width: '50%', height: '20px', justifySelf: 'center' }}
                      />
                    );
                  })}
                </div>
              </div>
            </div>

            <Table
              headers={[
                { key: 'number', label: '#', isNumeric: true },
                { key: 'id', label: 'Execution ID' },
                { key: 'trigger_type', label: 'Trigger' },
                { key: 'trigger_source', label: 'Trigger Source' },
                { key: 'status', label: 'Status' },
                { key: 'started_at', label: 'Started', isSortable: true },
                { key: 'completed_at', label: 'Completed' },
                { key: 'duration_ms', label: 'Duration', isNumeric: true },
                { key: 'memory_used_mb', label: 'Memory (MB)', isNumeric: true },
                { key: 'cpu_usage_percent', label: 'CPU %', isNumeric: true },
                { key: 'result', label: 'Result' },
                { key: 'error_message', label: 'Error' },
                { key: 'error_type', label: 'Error Type' },
                { key: 'created_at', label: 'Created' }
              ]}
              data={executions.map((execution, index) => ({
                ...execution,
                // Display numbers ascending (1..N) while rows remain newest-first
                number: index + 1,
                id: execution.id.substring(0, 8) + '...', // Truncate ID for display
                started_at: execution.started_at ? new Date(execution.started_at).toLocaleString() : 'N/A',
                completed_at: execution.completed_at ? new Date(execution.completed_at).toLocaleString() : 'N/A',
                duration_ms: execution.duration_ms ? `${execution.duration_ms}ms` : 'N/A',
                memory_used_mb: execution.memory_used_mb ? `${execution.memory_used_mb}MB` : 'N/A',
                cpu_usage_percent: execution.cpu_usage_percent ? `${execution.cpu_usage_percent}%` : 'N/A',
                result: execution.result ? 
                  (execution.result.length > 50 ? `${execution.result.substring(0, 50)}...` : execution.result) : 
                  'No result',
                error_message: execution.error_message ? 
                  (execution.error_message.length > 30 ? `${execution.error_message.substring(0, 30)}...` : execution.error_message) : 
                  '',
                error_type: execution.error_type || '',
                created_at: execution.created_at ? new Date(execution.created_at).toLocaleString() : 'N/A'
              }))}
              isLoading={executionsLoading}
              errorMessage={executionsError}
              onSort={(key) => {
                // For now, just sort by started_at descending (newest first)
                if (key === 'started_at') {
                  setExecutions(prev => [...prev].sort((a, b) => 
                    new Date(b.started_at || 0).getTime() - new Date(a.started_at || 0).getTime()
                  ));
                }
              }}
              sortKey="started_at"
              sortDirection="desc"
            />
            {/* Executions pagination controls */}
            <div className="mt-4">
              <Pagination
                currentPage={execPage}
                totalPages={execTotalPages}
                totalItems={execTotal}
                pageSize={execPageSize}
                onPageChange={(p) => setExecPage(p)}
                itemName="executions"
              />
            </div>
          </div>
        </TabPanel>

        <TabPanel activeTab={activeTab} index={1}>
          <div className="p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-secondary-800 dark:text-white">Function Code</h3>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">
                Code can be updated via the function settings
              </p>
            </div>

            <div className="border border-secondary-200 dark:border-secondary-700 rounded-lg overflow-hidden">
              <CodeEditor
                value={functionData?.code || '// No code available'}
                readOnly={true}
                height="400px"
                onChange={() => {}}
              />
            </div>
          </div>
        </TabPanel>

        <TabPanel activeTab={activeTab} index={2}>
          <div className="p-6">
            {!selectedWebhookId && (
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-secondary-800 dark:text-white">Webhooks</h3>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleCreateWebhook}
                    className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
                  >
                    Create Webhook
                  </button>
                </div>
              </div>
            )}

            {selectedWebhookId ? (
              <WebhookDetail
                inline
                inlineWebhookId={selectedWebhookId}
                onClose={() => setSelectedWebhookId(null)}
                onDeleted={(id) => {
                  setWebhooks(prev => prev.filter(w => w.id !== id));
                  setSelectedWebhookId(null);
                }}
              />
            ) : (
              <WebhookList
                webhooks={webhooks}
                onWebhookClick={(webhookId) => {
                  // Show inline detail instead of navigating away
                  setSelectedWebhookId(webhookId);
                }}
                onEditWebhook={handleEditWebhook}
                onWebhookDeleted={handleWebhookDeleted}
                loading={webhooksLoading}
                error={webhooksError}
              />
            )}
          </div>
        </TabPanel>
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={deleteDialogOpen}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Delete Function"
        description={
          <>
            <p className="text-secondary-600 dark:text-secondary-300">
              Are you sure you want to delete the function "{functionData.name}"? This action cannot be undone.
            </p>
            
            {deleteError && (
              <div className="mt-3 p-2 bg-error-100 dark:bg-error-900 text-error-700 dark:text-error-300 rounded-md text-sm">
                {deleteError}
              </div>
            )}
          </>
        }
        confirmButtonText={isDeleting ? "Deleting..." : "Delete"}
        isDestructive={true}
        isConfirmLoading={isDeleting}
      />

      {/* Webhook Delete Confirmation (inline) */}
      <ConfirmationDialog
        isOpen={deleteWebhookDialogOpen}
        onClose={() => setDeleteWebhookDialogOpen(false)}
        onConfirm={handleDeleteWebhookConfirm}
        title="Delete Webhook"
        description={
          <>
            <p className="text-secondary-600 dark:text-secondary-300">
              Are you sure you want to delete this webhook? This action cannot be undone.
            </p>
            {deleteWebhookError && (
              <div className="mt-3 p-2 bg-error-100 dark:bg-error-900 text-error-700 dark:text-error-300 rounded-md text-sm">
                {deleteWebhookError}
              </div>
            )}
          </>
        }
        confirmButtonText={isDeletingWebhook ? 'Deleting...' : 'Delete'}
        isDestructive={true}
        isConfirmLoading={isDeletingWebhook}
      />

      {/* Add the FunctionForm at the end of the component */}
      {functionId && functionData && (
        <FunctionForm
          isOpen={isFunctionInfoModalOpen}
          onClose={() => setIsFunctionInfoModalOpen(false)}
          onSuccess={(updatedFunction) => {
            setFunctionData(updatedFunction);
            handleFunctionInfoUpdate();
          }}
          editFunction={functionData}
        />
      )}

      {/* Webhook Form Modal */}
      {showWebhookForm && functionId && (
        <WebhookForm
          isOpen={showWebhookForm}
          onClose={handleWebhookFormClose}
          functionId={functionId}
          editWebhook={editingWebhook}
          onSuccess={() => {
            handleWebhookUpdated();
            handleWebhookFormClose();
          }}
        />
      )}
    </div>
  );
};

export default FunctionDetail;