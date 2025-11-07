import React, { useState, useEffect } from 'react';
import { Webhook, createWebhook, updateWebhook, CreateWebhookRequest, UpdateWebhookRequest } from '../../../../services/webhookService';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../../../../components/ui/dialog';
import { Label } from '../../../../components/ui/label';
import { Input } from '../../../../components/ui/input';
import { Textarea } from '../../../../components/ui/textarea';
import { Button } from '../../../../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../../components/ui/select';
import { IoMdEye, IoMdEyeOff } from 'react-icons/io';

interface WebhookFormProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (webhook: Webhook) => void;
  editWebhook: Webhook | null;
  functionId?: string; // Pre-selected function ID
}

const WebhookForm: React.FC<WebhookFormProps> = ({
  isOpen,
  onClose,
  onSuccess,
  editWebhook,
  functionId
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedFunctionId, setSelectedFunctionId] = useState(functionId || '');
  const [provider, setProvider] = useState('');
  const [providerEventType, setProviderEventType] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [showSecret, setShowSecret] = useState(false);
  const [rateLimitPerMinute, setRateLimitPerMinute] = useState(100);
  const [retryAttempts, setRetryAttempts] = useState(3);
  const [retryBackoffStrategy, setRetryBackoffStrategy] = useState<'exponential' | 'linear' | 'fixed'>('exponential');
  const [retryDelaySeconds, setRetryDelaySeconds] = useState(60);
  const [retryMaxDelaySeconds, setRetryMaxDelaySeconds] = useState(3600);
  const [isActive, setIsActive] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && !editWebhook) {
      resetForm();
      // Generate a random secret key for new webhooks
      setSecretKey('whsec_' + Math.random().toString(36).substring(2, 15));
    }
  }, [isOpen]);

  useEffect(() => {
    if (editWebhook) {
      setName(editWebhook.name);
      setDescription(editWebhook.description || '');
      setSelectedFunctionId(editWebhook.function_id);
      setProvider(editWebhook.provider || '');
      setProviderEventType(editWebhook.provider_event_type || '');
      setSourceUrl(editWebhook.source_url || '');
      // Load the actual secret_key for editing
      setSecretKey(editWebhook.secret_key || '');
      setRateLimitPerMinute(editWebhook.rate_limit_per_minute);
      setRetryAttempts(editWebhook.retry_attempts);
      setRetryBackoffStrategy(editWebhook.retry_backoff_strategy as 'exponential' | 'linear' | 'fixed');
      setRetryDelaySeconds(editWebhook.retry_delay_seconds);
      setRetryMaxDelaySeconds(editWebhook.retry_max_delay_seconds);
      setIsActive(editWebhook.is_active);
    }
  }, [editWebhook]);

  const resetForm = () => {
    setName('');
    setDescription('');
    setSelectedFunctionId(functionId || '');
    setProvider('');
    setProviderEventType('');
    setSourceUrl('');
    setSecretKey('');
    setRateLimitPerMinute(100);
    setRetryAttempts(3);
    setRetryBackoffStrategy('exponential');
    setRetryDelaySeconds(60);
    setRetryMaxDelaySeconds(3600);
    setIsActive(true);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      let result;

      if (editWebhook) {
        // For updates, only certain fields can be changed
        const updatePayload: UpdateWebhookRequest = {
          name,
          description: description || undefined,
          secret_key: secretKey || undefined, // Include if user provided a new one
          is_active: isActive,
          rate_limit_per_minute: rateLimitPerMinute,
          retry_attempts: retryAttempts,
          retry_delay_seconds: retryDelaySeconds,
        };
        result = await updateWebhook(editWebhook.id, updatePayload);
      } else {
        // For creation, include all fields
        const createPayload: CreateWebhookRequest = {
          name,
          function_id: selectedFunctionId,
          secret_key: secretKey,
          description: description || undefined,
          provider: provider || undefined,
          provider_event_type: providerEventType || undefined,
          source_url: sourceUrl || undefined,
          rate_limit_per_minute: rateLimitPerMinute,
          retry_attempts: retryAttempts,
          retry_backoff_strategy: retryBackoffStrategy,
          retry_delay_seconds: retryDelaySeconds,
          retry_max_delay_seconds: retryMaxDelaySeconds,
        };
        result = await createWebhook(createPayload);
      }

      onSuccess(result);
      onClose();
      resetForm();
    } catch (err: any) {
      console.error('Error saving webhook:', err);
      setError(err.response?.data?.detail || err.message || 'An error occurred while saving the webhook');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open: boolean) => !open && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {editWebhook ? 'Edit Webhook' : 'Create New Webhook'}
          </DialogTitle>
          <DialogDescription>
            {editWebhook ? 'Modify your webhook configuration below.' : 'Create a new webhook to trigger your function.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-4 bg-error-50 dark:bg-error-900/30 border border-error-200 dark:border-error-800 rounded-md text-error-700 dark:text-error-300 text-sm">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Webhook Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
                placeholder="my-webhook"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="function">Function</Label>
              <Input
                id="function"
                value={selectedFunctionId}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSelectedFunctionId(e.target.value)}
                placeholder="function-id"
                required
                disabled={!!editWebhook} // prevent changing function on edit
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDescription(e.target.value)}
              placeholder="Describe what this webhook does"
              rows={2}
            />
          </div>

          {/* Show provider/source/secret for both create and edit so everything is editable */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="provider">Provider (Optional)</Label>
              <Select value={provider} onValueChange={setProvider}>
                <SelectTrigger>
                  <SelectValue placeholder="Select provider" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="stripe">Stripe</SelectItem>
                  <SelectItem value="github">GitHub</SelectItem>
                  <SelectItem value="slack">Slack</SelectItem>
                  <SelectItem value="custom">Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="eventType">Event Type (Optional)</Label>
              <Input
                id="eventType"
                value={providerEventType}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setProviderEventType(e.target.value)}
                placeholder="checkout.session.completed"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="sourceUrl">Source URL (Optional)</Label>
            <Input
              id="sourceUrl"
              value={sourceUrl}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSourceUrl(e.target.value)}
              placeholder="https://api.stripe.com/webhooks"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="secretKey">Secret Key {editWebhook && <span className="text-xs text-secondary-500">(leave blank to keep current)</span>}</Label>
            <div className="relative">
              <Input
                id="secretKey"
                type={showSecret ? 'text' : 'password'}
                value={secretKey}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSecretKey(e.target.value)}
                placeholder="whsec_..."
                required={!editWebhook}
              />
              <button
                type="button"
                onClick={() => setShowSecret(prev => !prev)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200"
                aria-label={showSecret ? 'Hide secret' : 'Show secret'}
                title={showSecret ? 'Hide secret' : 'Show secret'}
              >
                {showSecret ? <IoMdEyeOff className="h-5 w-5" /> : <IoMdEye className="h-5 w-5" />}
              </button>
            </div>
            {editWebhook && <p className="text-xs text-secondary-500">You can update this secret to rotate credentials or fix setup errors.</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="rateLimit">Rate Limit (per minute)</Label>
              <Input
                id="rateLimit"
                type="number"
                min="1"
                max="10000"
                value={rateLimitPerMinute}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRateLimitPerMinute(Number(e.target.value))}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="retryAttempts">Retry Attempts</Label>
              <Input
                id="retryAttempts"
                type="number"
                min="1"
                max="10"
                value={retryAttempts}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRetryAttempts(Number(e.target.value))}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? (
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  {editWebhook ? 'Updating...' : 'Creating...'}
                </div>
              ) : (
                editWebhook ? 'Update Webhook' : 'Create Webhook'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default WebhookForm;