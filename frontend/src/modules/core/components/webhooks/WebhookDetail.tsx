import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Webhook, getWebhook, getWebhookDeliveries, WebhookDeliveryListResponse, WebhookDelivery, deleteWebhook } from '../../../../services/webhookService';
import { Loader } from '../ui/Loader';
import { Button } from '../../../../components/ui/button';
import WebhookForm from './WebhookForm';
import { ConfirmationDialog } from '../../../../components/ui/confirmation-dialog';
import { Trash2, ChevronRight, Pencil } from 'lucide-react';
// formatDistanceToNow removed — not needed in minimalist view
import { Table } from '../../../../components/ui/table';
import { Pagination } from '../../../../components/ui/pagination';
// Dialog removed: payload viewer removed to mirror FunctionDetail overview

interface WebhookDetailProps {
  inline?: boolean;
  inlineWebhookId?: string | null;
  onClose?: () => void;
  onDeleted?: (id: string) => void;
}

const WebhookDetail: React.FC<WebhookDetailProps> = ({ inline = false, inlineWebhookId = null, onClose, onDeleted }) => {
  const params = useParams<{ webhookId?: string; functionId?: string }>();
  const { functionId } = params;
  const webhookId = inline ? inlineWebhookId : params.webhookId || inlineWebhookId;
  const navigate = useNavigate();
  const [webhookData, setWebhookData] = useState<Webhook | null>(null);
  const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [deliveriesLoading, setDeliveriesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [showWebhookForm, setShowWebhookForm] = useState(false);
  const [editingWebhook, setEditingWebhook] = useState<Webhook | null>(null);

  // Pagination state
  const [page, setPage] = useState(1);
  const [pageSize] = useState(200);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  useEffect(() => {
    if (!webhookId) return;
    const fetchWebhookDetails = async () => {
      try {
        setLoading(true);
        const data = await getWebhook(webhookId);
        setWebhookData(data);
        setError(null);
      } catch (err: any) {
        console.error('Error fetching webhook details:', err);
        setError(err.response?.data?.detail || err.message || 'Failed to load webhook details');
      } finally {
        setLoading(false);
      }
    };

    fetchWebhookDetails();
  }, [webhookId]);

  const fetchDeliveries = async () => {
    if (!webhookId) return;

    try {
      setDeliveriesLoading(true);
      const response: WebhookDeliveryListResponse = await getWebhookDeliveries(webhookId, pageSize, (page - 1) * pageSize);
      setDeliveries(response.deliveries as WebhookDelivery[]);
      setTotal(response.total || 0);
      setTotalPages(Math.ceil((response.total || 0) / pageSize));
    } catch (err: any) {
      console.error('Error fetching webhook deliveries:', err);
    } finally {
      setDeliveriesLoading(false);
    }
  };

  useEffect(() => {
    if (webhookData) {
      fetchDeliveries();
    }
  }, [webhookData, page]);

  const handleDeleteClick = () => {
    setDeleteDialogOpen(true);
    setDeleteError(null);
  };

  const handleDeleteConfirm = async () => {
    if (!webhookId) return;

    setIsDeleting(true);
    setDeleteError(null);

    try {
      await deleteWebhook(webhookId);
      // If parent provided an onDeleted callback (inline mode), notify it and return
      if (onDeleted) {
        onDeleted(webhookId);
        return;
      }

      // Close inline detail if provided, otherwise navigate back to parent view
      if (onClose) onClose();
      else if (functionId) navigate(`/functions/${functionId}`);
      else navigate('/webhooks');
    } catch (err: any) {
      console.error('Error deleting webhook:', err);
      setDeleteError(err.response?.data?.detail || err.message || 'Failed to delete webhook');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setDeleteError(null);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <Loader size="large" />
      </div>
    );
  }

  if (error || !webhookData) {
    return (
      <div className="min-h-screen p-6">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white dark:bg-secondary-800 rounded-lg shadow border border-secondary-200 dark:border-secondary-700 p-6">
            <div className="text-center text-error-600 dark:text-error-400">
              <h2 className="text-xl font-semibold mb-2">Error Loading Webhook</h2>
              <p>{error || 'Webhook not found'}</p>
              <Button
                onClick={() => navigate('/webhooks')}
                className="mt-4"
              >
                Back to Webhooks
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-2">
      {/* Breadcrumbs and header: show only when not inline (embedded) to avoid duplication inside FunctionDetail */}
      {!inline && (
        <>
          <nav className="flex items-center text-sm text-secondary-500 dark:text-secondary-400 mb-4">
            <Link to="/functions" className="hover:text-primary-600 dark:hover:text-primary-400">
              Functions
            </Link>
            <ChevronRight className="w-4 h-4 mx-2" />
            <span className="text-secondary-800 dark:text-white">{webhookData.name}</span>
          </nav>

          {/* Header */}
          <div className="flex items-center mb-4">
            <div className="flex items-baseline flex-1 mr-4">
              <h2 className="text-2xl font-heading font-semibold text-secondary-800 dark:text-white tracking-tight">
                {webhookData.name}
              </h2>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={handleDeleteClick}
                className="p-2 rounded-md text-error-600 dark:text-error-400 border border-error-300 dark:border-error-500 hover:bg-error-50 dark:hover:bg-error-900/30 transition-colors"
                aria-label="Delete webhook"
                title="Delete webhook"
              >
                <Trash2 className="h-5 w-5" />
              </button>
            </div>
          </div>
        </>
      )}
      {/* Webhook edit modal (inline) */}
      {showWebhookForm && (
        <WebhookForm
          isOpen={showWebhookForm}
          onClose={() => { setShowWebhookForm(false); setEditingWebhook(null); }}
          functionId={webhookData?.function_id}
          editWebhook={editingWebhook}
          onSuccess={() => {
            // refresh deliveries and close
            fetchDeliveries();
            setShowWebhookForm(false);
            setEditingWebhook(null);
          }}
        />
      )}

      {inline ? (
        <>
          <div className="flex justify-between items-center mb-4">
          <div>
            <h3 className="text-lg font-semibold text-secondary-800 dark:text-white">Webhook Deliveries</h3>
            {/* when inline, show webhook name as subtitle to merge header */}
            {inline && <div className="text-sm text-secondary-500 mt-1">{webhookData.name}</div>}
          </div>

          <div className="flex items-center space-x-2">
            {inline ? (
              <>
                <button
                  onClick={onClose}
                  className="px-3 py-2 bg-secondary-700 text-white rounded-md hover:bg-secondary-600 transition-colors"
                  title="Close"
                >
                  ✕
                </button>
                <button
                  onClick={() => { setEditingWebhook(webhookData); setShowWebhookForm(true); }}
                  className="px-3 py-2 bg-secondary-700 text-white rounded-md hover:bg-secondary-600 transition-colors"
                  title="Edit webhook"
                >
                  <Pencil className="h-4 w-4 inline-block" />
                </button>
                <button
                  onClick={handleDeleteClick}
                  className="px-3 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                  title="Delete webhook"
                >
                  Delete
                </button>
              </>
            ) : (
              <></>
            )}
          </div>
          </div>

          {/* Status strip */}
          <div className="mb-4">
          <div className="w-full">
            <div
              className="w-full"
              style={{
                display: 'grid',
                gridTemplateColumns: `repeat(${pageSize}, 1fr)`,
                alignItems: 'center'
              }}
            >
              {Array.from({ length: pageSize }).map((_, slotIndex) => {
                const delivery = deliveries[slotIndex];
                if (delivery) {
                  let statusColor = 'bg-secondary-200 dark:bg-secondary-700';
                  if (delivery.status === 'completed') statusColor = 'bg-success-500 dark:bg-success-400';
                  else if (delivery.status === 'failed') statusColor = 'bg-error-500 dark:bg-error-400';
                  else if (delivery.status === 'processing') statusColor = 'bg-warning-500 dark:bg-warning-400';

                  return (
                    <div
                      key={delivery.id || slotIndex}
                      title={`${delivery.received_at || delivery.created_at || ''} — ${delivery.status}`}
                      className={`rounded-sm ${statusColor}`}
                      style={{ width: '50%', height: '20px', justifySelf: 'center' }}
                    />
                  );
                }

                return (
                  <div
                    key={`empty-${slotIndex}`}
                    title={`No delivery`}
                    className="rounded-sm bg-secondary-200 dark:bg-secondary-700"
                    style={{ width: '50%', height: '20px', justifySelf: 'center' }}
                  />
                );
              })}
            </div>
          </div>
          </div>

          {/* Full deliveries table — show all fields (truncated when needed) */}
          <Table
           headers={[
             { key: 'number', label: '#', isNumeric: true },
             { key: 'id', label: 'Delivery ID' },
             { key: 'webhook_id', label: 'Webhook ID' },
             { key: 'function_id', label: 'Function ID' },
             { key: 'source_ip', label: 'Source IP' },
             { key: 'source_user_agent', label: 'User Agent' },
             { key: 'request_method', label: 'Method' },
             { key: 'request_url', label: 'Request URL' },
             { key: 'request_body', label: 'Request Body' },
             { key: 'request_body_size_bytes', label: 'Req Size', isNumeric: true },
             { key: 'signature_header_name', label: 'Sig Header' },
             { key: 'signature_provided', label: 'Sig' },
             { key: 'signature_valid', label: 'Sig Valid' },
             { key: 'status', label: 'Status' },
             { key: 'delivery_attempt', label: 'Attempt', isNumeric: true },
             { key: 'response_status_code', label: 'HTTP', isNumeric: true },
             { key: 'execution_time_ms', label: 'Exec (ms)', isNumeric: true },
             { key: 'retry_count', label: 'Retries', isNumeric: true },
             { key: 'queued_at', label: 'Queued', isSortable: true },
             { key: 'processing_started_at', label: 'Started' },
             { key: 'processing_completed_at', label: 'Completed' },
             { key: 'received_at', label: 'Received' },
             { key: 'created_at', label: 'Created' },
             { key: 'updated_at', label: 'Updated' }
           ]}
           data={deliveries.map((delivery, index) => ({
             ...delivery,
             number: index + 1,
             id: delivery.id.substring(0, 8) + '...',
             webhook_id: delivery.webhook_id?.substring(0, 8) + '...',
             function_id: delivery.function_id?.substring(0, 8) + '...',
             source_user_agent: delivery.source_user_agent || 'N/A',
             request_url: delivery.request_url ? (delivery.request_url.length > 60 ? `${delivery.request_url.substring(0, 60)}...` : delivery.request_url) : 'N/A',
             request_body: delivery.request_body ? (typeof delivery.request_body === 'string' ? delivery.request_body : JSON.stringify(delivery.request_body)).substring(0, 100) + '...' : '—',
             request_body_size_bytes: delivery.request_body_size_bytes || '—',
             signature_provided: delivery.signature_provided || '—',
             signature_valid: delivery.signature_valid ? '✓' : '✗',
             status: delivery.status,
             delivery_attempt: delivery.delivery_attempt || 0,
             response_status_code: delivery.response_status_code || '—',
             execution_time_ms: delivery.execution_time_ms || '—',
             retry_count: delivery.retry_count || 0,
             queued_at: delivery.queued_at ? new Date(delivery.queued_at).toLocaleString() : 'N/A',
             processing_started_at: delivery.processing_started_at ? new Date(delivery.processing_started_at).toLocaleString() : 'N/A',
             processing_completed_at: delivery.processing_completed_at ? new Date(delivery.processing_completed_at).toLocaleString() : 'N/A',
             received_at: delivery.received_at ? new Date(delivery.received_at).toLocaleString() : 'N/A',
             created_at: delivery.created_at ? new Date(delivery.created_at).toLocaleString() : 'N/A',
             updated_at: delivery.updated_at ? new Date(delivery.updated_at).toLocaleString() : 'N/A'
           }))}
          isLoading={deliveriesLoading}
          errorMessage={null}
          onSort={(key) => {
            if (key === 'queued_at') {
              setDeliveries(prev => [...prev].sort((a, b) => new Date(b.queued_at || 0).getTime() - new Date(a.queued_at || 0).getTime()));
            }
          }}
          sortKey="queued_at"
          sortDirection="desc"
          />

          <div className="mt-4">
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              totalItems={total}
              pageSize={pageSize}
              onPageChange={(p) => setPage(p)}
              itemName="deliveries"
            />
          </div>
        </>
      ) : (
        <div className="bg-white dark:bg-secondary-800 p-6 rounded-lg shadow border border-secondary-200 dark:border-secondary-700">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h3 className="text-lg font-semibold text-secondary-800 dark:text-white">Webhook Deliveries</h3>
              {inline && <div className="text-sm text-secondary-500 mt-1">{webhookData.name}</div>}
            </div>

            <div className="flex items-center space-x-2">
              {inline ? (
                <>
                  <button
                    onClick={onClose}
                    className="px-3 py-2 bg-secondary-700 text-white rounded-md hover:bg-secondary-600 transition-colors"
                    title="Close"
                  >
                    ✕
                  </button>
                  <button
                    onClick={handleDeleteClick}
                    className="px-3 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                    title="Delete webhook"
                  >
                    Delete
                  </button>
                </>
              ) : (
                <></>
              )}
            </div>
          </div>

          {/* Status strip */}
          <div className="mb-4">
            <div className="w-full">
              <div
                className="w-full"
                style={{
                  display: 'grid',
                  gridTemplateColumns: `repeat(${pageSize}, 1fr)`,
                  alignItems: 'center'
                }}
              >
                {Array.from({ length: pageSize }).map((_, slotIndex) => {
                  const delivery = deliveries[slotIndex];
                  if (delivery) {
                    let statusColor = 'bg-secondary-200 dark:bg-secondary-700';
                    if (delivery.status === 'completed') statusColor = 'bg-success-500 dark:bg-success-400';
                    else if (delivery.status === 'failed') statusColor = 'bg-error-500 dark:bg-error-400';
                    else if (delivery.status === 'processing') statusColor = 'bg-warning-500 dark:bg-warning-400';

                    return (
                      <div
                        key={delivery.id || slotIndex}
                        title={`${delivery.received_at || delivery.created_at || ''} — ${delivery.status}`}
                        className={`rounded-sm ${statusColor}`}
                        style={{ width: '50%', height: '20px', justifySelf: 'center' }}
                      />
                    );
                  }

                  return (
                    <div
                      key={`empty-${slotIndex}`}
                      title={`No delivery`}
                      className="rounded-sm bg-secondary-200 dark:bg-secondary-700"
                      style={{ width: '50%', height: '20px', justifySelf: 'center' }}
                    />
                  );
                })}
              </div>
            </div>
          </div>

          {/* Full deliveries table — show all fields (truncated when needed) */}
           <Table
             headers={[
               { key: 'number', label: '#', isNumeric: true },
               { key: 'id', label: 'Delivery ID' },
               { key: 'webhook_id', label: 'Webhook ID' },
               { key: 'function_id', label: 'Function ID' },
               { key: 'source_ip', label: 'Source IP' },
               { key: 'source_user_agent', label: 'User Agent' },
               { key: 'request_method', label: 'Method' },
               { key: 'request_url', label: 'Request URL' },
               { key: 'request_body', label: 'Request Body' },
               { key: 'request_body_size_bytes', label: 'Req Size', isNumeric: true },
               { key: 'signature_header_name', label: 'Sig Header' },
               { key: 'signature_provided', label: 'Sig' },
               { key: 'signature_valid', label: 'Sig Valid' },
               { key: 'status', label: 'Status' },
               { key: 'delivery_attempt', label: 'Attempt', isNumeric: true },
               { key: 'response_status_code', label: 'HTTP', isNumeric: true },
               { key: 'execution_time_ms', label: 'Exec (ms)', isNumeric: true },
               { key: 'retry_count', label: 'Retries', isNumeric: true },
               { key: 'queued_at', label: 'Queued', isSortable: true },
               { key: 'processing_started_at', label: 'Started' },
               { key: 'processing_completed_at', label: 'Completed' },
               { key: 'received_at', label: 'Received' },
               { key: 'created_at', label: 'Created' },
               { key: 'updated_at', label: 'Updated' }
             ]}
             data={deliveries.map((delivery, index) => ({
               ...delivery,
               number: index + 1,
               id: delivery.id.substring(0, 8) + '...',
               webhook_id: delivery.webhook_id?.substring(0, 8) + '...',
               function_id: delivery.function_id?.substring(0, 8) + '...',
               source_user_agent: delivery.source_user_agent || 'N/A',
               request_url: delivery.request_url ? (delivery.request_url.length > 60 ? `${delivery.request_url.substring(0, 60)}...` : delivery.request_url) : 'N/A',
               request_body: delivery.request_body ? (typeof delivery.request_body === 'string' ? delivery.request_body : JSON.stringify(delivery.request_body)).substring(0, 100) + '...' : '—',
               request_body_size_bytes: delivery.request_body_size_bytes || '—',
               signature_provided: delivery.signature_provided || '—',
               signature_valid: delivery.signature_valid ? '✓' : '✗',
               status: delivery.status,
               delivery_attempt: delivery.delivery_attempt || 0,
               response_status_code: delivery.response_status_code || '—',
               execution_time_ms: delivery.execution_time_ms || '—',
               retry_count: delivery.retry_count || 0,
               queued_at: delivery.queued_at ? new Date(delivery.queued_at).toLocaleString() : 'N/A',
               processing_started_at: delivery.processing_started_at ? new Date(delivery.processing_started_at).toLocaleString() : 'N/A',
               processing_completed_at: delivery.processing_completed_at ? new Date(delivery.processing_completed_at).toLocaleString() : 'N/A',
               received_at: delivery.received_at ? new Date(delivery.received_at).toLocaleString() : 'N/A',
               created_at: delivery.created_at ? new Date(delivery.created_at).toLocaleString() : 'N/A',
               updated_at: delivery.updated_at ? new Date(delivery.updated_at).toLocaleString() : 'N/A'
             }))}
            isLoading={deliveriesLoading}
            errorMessage={null}
            onSort={(key) => {
              if (key === 'queued_at') {
                setDeliveries(prev => [...prev].sort((a, b) => new Date(b.queued_at || 0).getTime() - new Date(a.queued_at || 0).getTime()));
              }
            }}
            sortKey="queued_at"
            sortDirection="desc"
          />

          <div className="mt-4">
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              totalItems={total}
              pageSize={pageSize}
              onPageChange={(p) => setPage(p)}
              itemName="deliveries"
            />
          </div>
        </div>
      )}

      {/* Payload viewer removed — all fields are now shown in the table */}

      <ConfirmationDialog
        isOpen={deleteDialogOpen}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Delete Webhook"
        description={
          <>
            <p className="text-secondary-600 dark:text-secondary-300">Are you sure you want to delete the webhook "{webhookData.name}"? This action cannot be undone.</p>
            {deleteError && (
              <div className="mt-3 p-2 bg-error-100 dark:bg-error-900 text-error-700 dark:text-error-300 rounded-md text-sm">{deleteError}</div>
            )}
          </>
        }
        confirmButtonText={isDeleting ? "Deleting..." : "Delete"}
        isDestructive={true}
        isConfirmLoading={isDeleting}
      />
    </div>
  );
};

export default WebhookDetail;