import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef
} from 'react';
import { useAuth } from '../../auth/context/AuthContext';
import realtimeService from '../../../services/realtimeService';
import {
  TableIcon,
  FunctionIcon,
  DatabaseIcon,
  UserIcon,
  StorageIcon,
  WebhookIcon,
  ClockIcon
} from '../components/icons';

const MAX_ACTIVITY_ITEMS = 500;
const STORAGE_KEY_BASE = 'selfdb.activityFeed';
const DEFAULT_ICON_CLASS = 'w-5 h-5 text-secondary-600 dark:text-secondary-300';

type ChannelConfig = {
  label: string;
  icon: () => React.ReactNode;
};

const CHANNEL_CONFIG: Record<string, ChannelConfig> = {
  users_events: {
    label: 'User',
    icon: () => <UserIcon className={DEFAULT_ICON_CLASS} />
  },
  tables_events: {
    label: 'Table',
    icon: () => <TableIcon className={DEFAULT_ICON_CLASS} />
  },
  files_events: {
    label: 'File',
    icon: () => <StorageIcon className={DEFAULT_ICON_CLASS} />
  },
  buckets_events: {
    label: 'Bucket',
    icon: () => <DatabaseIcon className={DEFAULT_ICON_CLASS} />
  },
  functions_events: {
    label: 'Function',
    icon: () => <FunctionIcon className={DEFAULT_ICON_CLASS} />
  },
  webhooks_events: {
    label: 'Webhook',
    icon: () => <WebhookIcon className={DEFAULT_ICON_CLASS} />
  },
  webhook_deliveries_events: {
    label: 'Webhook Delivery',
    icon: () => <WebhookIcon className={DEFAULT_ICON_CLASS} />
  }
};

const ACTION_TITLE_MAP: Record<string, string> = {
  INSERT: 'Created',
  UPDATE: 'Updated',
  DELETE: 'Deleted'
};

const ACTION_VERB_MAP: Record<string, string> = {
  INSERT: 'created',
  UPDATE: 'updated',
  DELETE: 'deleted'
};

const createDefaultIcon = () => <ClockIcon className={DEFAULT_ICON_CLASS} />;

const humanizeTableName = (value?: string): string => {
  if (!value) return 'Record';
  return value
    .replace(/_/g, ' ')
    .split(' ')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
};

const formatRelativeTime = (timestamp?: string | number): string => {
  if (timestamp == null) return 'just now';
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return 'just now';
  }

  const diffMs = Date.now() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);

  if (diffSeconds < 5) return 'just now';
  if (diffSeconds < 60) return `${diffSeconds}s ago`;

  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes}m ago`;

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
};

const parseRealtimePayload = (payload: any): Record<string, any> | null => {
  if (payload == null) {
    return null;
  }

  let value: any = payload;

  if (typeof value === 'object' && value !== null && 'payload' in value) {
    value = (value as Record<string, any>).payload;
  }

  for (let i = 0; i < 3; i++) {
    if (typeof value === 'string') {
      try {
        value = JSON.parse(value);
        continue;
      } catch (error) {
        console.warn('Failed to parse realtime payload string', error, value);
      }
    }
    break;
  }

  if (value && typeof value === 'object') {
    return value as Record<string, any>;
  }

  return null;
};

const getEntityName = (channel: string, data: Record<string, any>): string | undefined => {
  const newData = data?.new_data ?? {};
  const oldData = data?.old_data ?? {};
  const source = data?.action === 'DELETE' ? oldData : newData;

  switch (channel) {
    case 'users_events': {
      const nameParts = [source.first_name, source.last_name].filter(Boolean).join(' ').trim();
      if (nameParts.length > 0) {
        return nameParts;
      }
      return source.email || source.username || source.id;
    }
    case 'tables_events':
      return newData.name || oldData.name || data.table;
    case 'files_events': {
      const rawValue = newData.name || oldData.name || newData.file_name || oldData.file_name;
      if (typeof rawValue === 'string') {
        const parts = rawValue.split('/').filter(Boolean);
        if (parts.length > 0) {
          return parts[parts.length - 1];
        }
      }
      return rawValue;
    }
    case 'buckets_events':
      return newData.name || oldData.name;
    case 'functions_events':
      return newData.name || oldData.name;
    case 'webhook_deliveries_events':
      return newData.id || oldData.id;
    default:
      return newData.name || oldData.name || newData.id || oldData.id || data.table;
  }
};

type ActivityEntryOptions = {
  resolveBucketName?: (id?: string | null) => string | undefined;
};

export type ActivityEntry = {
  id: string;
  title: string;
  description: string;
  timestamp: string;
  icon?: React.ReactNode;
  eventAt?: number;
};

const createActivityEntry = (
  channel: string,
  data: Record<string, any>,
  options: ActivityEntryOptions = {}
): ActivityEntry | null => {
  if (!data) {
    return null;
  }

  const config = CHANNEL_CONFIG[channel];
  const action = data.action ?? 'UPDATE';
  const label = config?.label ?? humanizeTableName(data.table);
  const titleSuffix = ACTION_TITLE_MAP[action] ?? 'Updated';
  const verb = ACTION_VERB_MAP[action] ?? 'updated';
  const entityName = getEntityName(channel, data);
  const quotedName = entityName ? `"${entityName}"` : humanizeTableName(data.table);
  const eventAt = data.timestamp ? new Date(data.timestamp).getTime() : Date.now();

  const buildDescription = (): string => {
    switch (channel) {
      case 'users_events': {
        const user = action === 'DELETE' ? (data.old_data ?? {}) : (data.new_data ?? {});
        const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ').trim();
        const email = user.email;
        const display = fullName || email || user.username || user.id || 'user';
        const emailSuffix = email && fullName ? ` (${email})` : '';
        return `User "${display}"${emailSuffix} was ${verb}.`;
      }
      case 'tables_events': {
        return `Table ${quotedName} was ${verb}.`;
      }
      case 'files_events': {
        const file = action === 'DELETE' ? (data.old_data ?? {}) : (data.new_data ?? {});
        const rawName = file.name || file.file_name || file.path;
        const pathSegments = typeof rawName === 'string' ? rawName.split('/').filter(Boolean) : [];
        const simpleName = pathSegments.length > 0 ? pathSegments[pathSegments.length - 1] : rawName || 'file';
        const bucketId = file.bucket_id || file.bucket || file.bucketId || file.bucket_uuid;
        const bucketFromPath = pathSegments.length > 1 ? pathSegments[0] : undefined;
        const bucketName = file.bucket_name || options.resolveBucketName?.(bucketId) || bucketFromPath || bucketId;

        if (action === 'INSERT') {
          return bucketName
            ? `File "${simpleName}" added to bucket "${bucketName}".`
            : `File "${simpleName}" was added.`;
        }

        if (action === 'DELETE') {
          return bucketName
            ? `File "${simpleName}" removed from bucket "${bucketName}".`
            : `File "${simpleName}" was deleted.`;
        }

        const bucketSuffix = bucketName ? ` in bucket "${bucketName}"` : '';
        return `File "${simpleName}"${bucketSuffix} was ${verb}.`;
      }
      case 'buckets_events': {
        const bucket = action === 'DELETE' ? (data.old_data ?? {}) : (data.new_data ?? {});
        const owner = bucket.owner_id ? ` (owner ${bucket.owner_id})` : '';
        return `Bucket ${quotedName}${owner} was ${verb}.`;
      }
      case 'functions_events': {
        const fn = action === 'DELETE' ? (data.old_data ?? {}) : (data.new_data ?? {});
        const runtime = fn.runtime ? ` (runtime ${fn.runtime})` : '';
        return `Function ${quotedName}${runtime} was ${verb}.`;
      }
      case 'webhooks_events': {
        const webhook = action === 'DELETE' ? (data.old_data ?? {}) : (data.new_data ?? {});
        const name = webhook.name || webhook.path_segment || webhook.id || 'webhook';
        const provider = webhook.provider ? ` (${webhook.provider})` : '';
        const fnHint = webhook.function_name || webhook.function_id;
        const functionSuffix = fnHint ? ` for function ${fnHint}` : '';
        return `Webhook "${name}"${provider}${functionSuffix} was ${verb}.`;
      }
      case 'webhook_deliveries_events': {
        const delivery = action === 'DELETE' ? (data.old_data ?? {}) : (data.new_data ?? {});
        const deliveryId = delivery.id || delivery.delivery_id || 'delivery';
        const status = delivery.status ? String(delivery.status).toLowerCase() : undefined;
        const statusText = status ? `status ${status}` : verb;
        const functionSuffix = delivery.function_id ? ` for function ${delivery.function_id}` : '';
        return `Webhook delivery "${deliveryId}"${functionSuffix} ${statusText}.`;
      }
      default:
        return `${label} ${quotedName} was ${verb}.`;
    }
  };

  const description = buildDescription();
  const timestamp = formatRelativeTime(eventAt);
  const icon = (config?.icon ?? createDefaultIcon)();

  return {
    id: `${channel}-${data.timestamp ?? Date.now()}-${entityName ?? Math.random().toString(36).slice(2)}`,
    title: entityName ? `${label} ${titleSuffix} — ${entityName}` : `${label} ${titleSuffix}`,
    description,
    timestamp,
    icon,
    eventAt
  };
};

interface ActivityRecord {
  channel: string;
  data: Record<string, any>;
  entry: ActivityEntry;
}

type ActivityState = ActivityRecord[];

type ActivityAction =
  | { type: 'INITIALIZE'; payload: ActivityRecord[] }
  | { type: 'ADD'; payload: ActivityRecord }
  | { type: 'REFRESH_TIMESTAMPS' }
  | { type: 'CLEAR' };

const activityReducer = (state: ActivityState, action: ActivityAction): ActivityState => {
  switch (action.type) {
    case 'INITIALIZE':
      return action.payload.slice(0, MAX_ACTIVITY_ITEMS);
    case 'ADD': {
      if (state.some((record) => record.entry.id === action.payload.entry.id)) {
        return state;
      }
      const next = [action.payload, ...state];
      return next.slice(0, MAX_ACTIVITY_ITEMS);
    }
    case 'REFRESH_TIMESTAMPS':
      return state.map((record) => ({
        ...record,
        entry: {
          ...record.entry,
          timestamp: formatRelativeTime(record.entry.eventAt ?? Date.now())
        }
      }));
    case 'CLEAR':
      return [];
    default:
      return state;
  }
};

export interface RealtimeChannelEvent {
  channel: string;
  data: Record<string, any> | null;
  raw: any;
}

interface ActivityFeedContextValue {
  activities: ActivityEntry[];
  clearActivities: () => void;
  registerListener: (channel: string, handler: (event: RealtimeChannelEvent) => void) => () => void;
  primeBucketNames: (buckets: Array<Record<string, any>>) => void;
}

const ActivityFeedContext = createContext<ActivityFeedContextValue | undefined>(undefined);

const getStorageKey = (userId?: string | null) => {
  if (!userId) return null;
  return `${STORAGE_KEY_BASE}.${userId}`;
};

const safeParseStoredActivities = (
  serialized: string | null,
  upsertBucketName: (bucketData: Record<string, any> | null | undefined) => void,
  resolveBucketName: (id?: string | null) => string | undefined
): ActivityRecord[] => {
  if (!serialized) {
    return [];
  }

  try {
    const parsed = JSON.parse(serialized);
    if (!Array.isArray(parsed)) {
      return [];
    }

    const records: ActivityRecord[] = [];
    for (const item of parsed) {
      if (!item || typeof item.channel !== 'string' || typeof item.data !== 'object') {
        continue;
      }

      const data = item.data as Record<string, any>;

      if (item.channel === 'buckets_events') {
        upsertBucketName(data.new_data);
        upsertBucketName(data.old_data);
      } else if (item.channel === 'files_events') {
        const candidates = [data.new_data, data.old_data];
        candidates.forEach((file) => {
          if (file?.bucket_id && file?.bucket_name) {
            upsertBucketName({ id: file.bucket_id, name: file.bucket_name });
          }
        });
      }

      const entry = createActivityEntry(item.channel, data, { resolveBucketName });
      if (entry) {
        records.push({ channel: item.channel, data, entry });
      }
    }

    return records;
  } catch (error) {
    console.error('Failed to parse stored activity feed', error);
    return [];
  }
};

export const ActivityFeedProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, currentUser } = useAuth();
  const storageKey = useMemo(() => getStorageKey(currentUser?.id ?? null), [currentUser]);

  const [state, dispatch] = useReducer(activityReducer, []);
  const bucketNameRef = useRef<Record<string, string>>({});
  const listenersRef = useRef<Record<string, Set<(event: RealtimeChannelEvent) => void>>>({});
  const previousStorageKeyRef = useRef<string | null>(null);

  const resolveBucketName = useCallback((id?: string | null) => {
    if (!id) return undefined;
    return bucketNameRef.current[id];
  }, []);

  const upsertBucketName = useCallback((bucketData: Record<string, any> | null | undefined) => {
    if (!bucketData) return;
    const id = bucketData.id;
    if (!id) return;
    const name = bucketData.name || bucketData.slug || bucketData.identifier;
    if (name) {
      bucketNameRef.current[id] = name;
    }
  }, []);

  const primeBucketNames = useCallback((buckets: Array<Record<string, any>>) => {
    buckets.forEach((bucket) => upsertBucketName(bucket));
  }, [upsertBucketName]);

  const notifyListeners = useCallback((channel: string, data: Record<string, any> | null, raw: any) => {
    const listeners = listenersRef.current[channel];
    if (!listeners || listeners.size === 0) {
      return;
    }

    listeners.forEach((listener) => {
      try {
        listener({ channel, data, raw });
      } catch (error) {
        console.error('Error in activity feed listener', error);
      }
    });
  }, []);

  const handleRealtimeMessage = useCallback((channel: string, payload: any) => {
    const data = parseRealtimePayload(payload);

    if (data) {
      if (channel === 'buckets_events') {
        upsertBucketName(data.new_data);
        upsertBucketName(data.old_data);
      } else if (channel === 'files_events') {
        const candidates = [data.new_data, data.old_data];
        candidates.forEach((file) => {
          if (file?.bucket_id && file?.bucket_name) {
            upsertBucketName({ id: file.bucket_id, name: file.bucket_name });
          }
        });
      }
    }

    notifyListeners(channel, data, payload);

    if (!data) {
      return;
    }

    const entry = createActivityEntry(channel, data, { resolveBucketName });
    if (!entry) {
      return;
    }

    const record: ActivityRecord = { channel, data, entry };
    dispatch({ type: 'ADD', payload: record });
  }, [notifyListeners, resolveBucketName, upsertBucketName]);

  useEffect(() => {
    if (!isAuthenticated) {
      if (previousStorageKeyRef.current) {
        try {
          sessionStorage.removeItem(previousStorageKeyRef.current);
        } catch (error) {
          console.warn('Failed to remove stored activity feed', error);
        }
      }
      previousStorageKeyRef.current = null;
      bucketNameRef.current = {};
      listenersRef.current = {};
      dispatch({ type: 'CLEAR' });
      return;
    }

    if (!storageKey) {
      return;
    }

    previousStorageKeyRef.current = storageKey;
    const stored = typeof window !== 'undefined' ? sessionStorage.getItem(storageKey) : null;
    const records = safeParseStoredActivities(stored, upsertBucketName, resolveBucketName);
    dispatch({ type: 'INITIALIZE', payload: records });
  }, [isAuthenticated, storageKey, resolveBucketName, upsertBucketName]);

  useEffect(() => {
    if (!isAuthenticated || !storageKey) {
      return;
    }

    try {
      const serialized = state.map((record) => ({
        channel: record.channel,
        data: record.data
      }));
      sessionStorage.setItem(storageKey, JSON.stringify(serialized));
    } catch (error) {
      console.warn('Failed to persist activity feed', error);
    }
  }, [state, isAuthenticated, storageKey]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    const interval = window.setInterval(() => {
      dispatch({ type: 'REFRESH_TIMESTAMPS' });
    }, 10000);

    return () => window.clearInterval(interval);
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    const channels = [
      'users_events',
      'tables_events',
      'files_events',
      'buckets_events',
      'functions_events',
      'webhooks_events',
      'webhook_deliveries_events'
    ];

    channels.forEach((channel) => {
      realtimeService.subscribe(channel);
    });

    const removers = channels.map((channel) =>
      realtimeService.addListener(channel, (payload: any) => handleRealtimeMessage(channel, payload))
    );

    return () => {
      removers.forEach((remove) => remove());
      channels.forEach((channel) => realtimeService.unsubscribe(channel));
    };
  }, [isAuthenticated, handleRealtimeMessage]);

  const registerListener = useCallback(
    (channel: string, handler: (event: RealtimeChannelEvent) => void) => {
      if (!listenersRef.current[channel]) {
        listenersRef.current[channel] = new Set();
      }
      listenersRef.current[channel]!.add(handler);

      return () => {
        const listeners = listenersRef.current[channel];
        if (!listeners) {
          return;
        }
        listeners.delete(handler);
        if (listeners.size === 0) {
          delete listenersRef.current[channel];
        }
      };
    },
    []
  );

  const clearActivities = useCallback(() => {
    dispatch({ type: 'CLEAR' });
    if (storageKey) {
      try {
        sessionStorage.removeItem(storageKey);
      } catch (error) {
        console.warn('Failed to clear stored activity feed', error);
      }
    }
  }, [storageKey]);

  const activities = useMemo(() => state.map((record) => record.entry), [state]);

  const value = useMemo<ActivityFeedContextValue>(() => ({
    activities,
    clearActivities,
    registerListener,
    primeBucketNames
  }), [activities, clearActivities, registerListener, primeBucketNames]);

  return (
    <ActivityFeedContext.Provider value={value}>
      {children}
    </ActivityFeedContext.Provider>
  );
};

export const useActivityFeed = (): ActivityFeedContextValue => {
  const context = useContext(ActivityFeedContext);
  if (!context) {
    throw new Error('useActivityFeed must be used within an ActivityFeedProvider');
  }
  return context;
};

