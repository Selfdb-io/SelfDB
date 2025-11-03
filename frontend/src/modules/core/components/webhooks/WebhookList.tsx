import React, { useState } from 'react';
import { Zap } from 'lucide-react';
import { Webhook, deleteWebhook } from '../../../../services/webhookService';
import { ConfirmationDialog } from '../../../../components/ui/confirmation-dialog';
import { formatDistanceToNow } from 'date-fns';
import { Table, TableHeader } from '../../../../components/ui/table';

interface WebhookListProps {
  webhooks: Webhook[];
  onWebhookClick: (webhookId: string) => void;
  onEditWebhook: (webhook: Webhook) => void;
  onWebhookDeleted: (webhookId: string) => void;
  loading: boolean;
  error: string | null;
}

interface FormattedWebhook extends Webhook {
  lastReceived: string;
  statusLabel: React.ReactNode;
}

const WebhookList: React.FC<WebhookListProps> = ({
  webhooks,
  onWebhookClick,
  onEditWebhook,
  onWebhookDeleted,
  loading,
  error
}) => {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [webhookToDelete, setWebhookToDelete] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  if (loading) {
    return (
      <div className="flex justify-center items-center p-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg text-error-700 dark:text-error-300">
        <h3 className="text-lg font-heading font-semibold mb-2">Error Loading Webhooks</h3>
        <p>{error}</p>
      </div>
    );
  }

  if (webhooks.length === 0 && !loading) {
    return (
      <div className="text-secondary-500 dark:text-secondary-400 py-8 text-center text-base">
        No webhooks found. Create your first webhook to get started.
      </div>
    );
  }

  const handleDeleteConfirm = async () => {
    if (!webhookToDelete) return;

    try {
      setIsDeleting(true);
      setDeleteError(null);
      await deleteWebhook(webhookToDelete);
      onWebhookDeleted(webhookToDelete);
      setDeleteDialogOpen(false);
    } catch (err: any) {
      console.error('Error deleting webhook:', err);
      setDeleteError(err.response?.data?.detail || err.message || 'Failed to delete webhook');
    } finally {
      setIsDeleting(false);
      setWebhookToDelete(null);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setWebhookToDelete(null);
    setDeleteError(null);
  };

  const tableHeaders: TableHeader[] = [
    { key: 'name', label: 'Name' },
    { key: 'provider', label: 'Provider' },
    { key: 'statusLabel', label: 'Status' },
    { key: 'deliveries', label: 'Deliveries' },
    { key: 'lastReceived', label: 'Last Received' },
  ];

  const formattedData: FormattedWebhook[] = webhooks.map(webhook => ({
    ...webhook,
    lastReceived: webhook.last_received_at
      ? formatDistanceToNow(new Date(webhook.last_received_at), { addSuffix: true })
      : 'Never',
    statusLabel: (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
        ${webhook.is_active
          ? 'bg-success-100 dark:bg-success-900/20 text-success-800 dark:text-success-300'
          : 'bg-warning-100 dark:bg-warning-900/20 text-warning-800 dark:text-warning-300'}`}
      >
        {webhook.is_active ? 'Active' : 'Inactive'}
      </span>
    ),
    deliveries: `${webhook.successful_delivery_count}/${webhook.total_delivery_count}`,
  }));

  const renderRowIcon = () => <Zap className="h-5 w-5 text-primary-600" />;

  const renderActions = (item: FormattedWebhook) => (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onEditWebhook(item);
      }}
      className="text-secondary-600 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-300 p-1 rounded hover:bg-secondary-100 dark:hover:bg-secondary-700"
      aria-label="Edit webhook"
    >
      Edit
    </button>
  );

  const handleRowClick = (item: FormattedWebhook) => {
    onWebhookClick(item.id);
  };

  return (
    <>
      <Table
        data={formattedData}
        headers={tableHeaders}
        onRowClick={handleRowClick}
        renderRowIcon={renderRowIcon}
        renderActions={renderActions}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={deleteDialogOpen}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Delete Webhook"
        description={
          <>
            <p className="text-secondary-600 dark:text-secondary-300">
              Are you sure you want to delete this webhook? This action cannot be undone.
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
    </>
  );
};

export default WebhookList;