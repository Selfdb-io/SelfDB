import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../../../auth/context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { SummaryCardGroup, ActionButtonGroup, ActivitySection } from '../sections';
import { TableIcon, AuthIcon, FunctionIcon, SettingsIcon } from '../icons';
import { useActivityFeed } from '../../context/ActivityFeedContext';
import { getRegularUsersCount } from '../../../../services/userService';
import { getTables } from '../../../../services/tableService';
import { getUserBuckets } from '../../../../services/bucketService';
import { getFunctions } from '../../../../services/functionService';
import { FaPython, FaReact, FaSwift, FaCode } from 'react-icons/fa';

// Helper function to format bytes
const formatBytes = (bytes: number, decimals = 2): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

const Dashboard: React.FC = () => {
  const auth = useAuth();
  const navigate = useNavigate();
  const { activities, registerListener, primeBucketNames } = useActivityFeed();

  const [userCount, setUserCount] = useState<number>(0);
  const [tableCount, setTableCount] = useState<number>(0);
  const [storageSize, setStorageSize] = useState<number>(0);
  const [functionCount, setFunctionCount] = useState<number>(0);
  const [isLoadingUsers, setIsLoadingUsers] = useState(true);
  const [isLoadingTables, setIsLoadingTables] = useState(true);
  const [isLoadingStorage, setIsLoadingStorage] = useState(true);
  const [isLoadingFunctions, setIsLoadingFunctions] = useState(true);

  const refreshStorageSize = useCallback(async () => {
    try {
      console.log('Refreshing storage size from database...');
      const buckets = await getUserBuckets();
      console.log('Fetched buckets from database:', buckets);
      primeBucketNames(buckets);

      const total = buckets.reduce((sum, bucket) => sum + (bucket.total_size ?? 0), 0);
      console.log('Total storage size calculated:', total);

      setStorageSize(total);
    } catch (err) {
      console.error('Error updating storage size:', err);
    } finally {
      setIsLoadingStorage(false);
    }
  }, [primeBucketNames]);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoadingUsers(true);
      setIsLoadingTables(true);
      setIsLoadingStorage(true);
      setIsLoadingFunctions(true);
      try {
        const userCount = await getRegularUsersCount();
        setUserCount(userCount);
        setIsLoadingUsers(false);

        const tables = await getTables();
        setTableCount(tables.length);
        setIsLoadingTables(false);

        // Fetch buckets and calculate total size from files
        await refreshStorageSize();

        // Fetch functions count
        const functions = await getFunctions();
        setFunctionCount(functions.total);
        setIsLoadingFunctions(false);

      } catch (error) {
        console.error('Failed to fetch initial data:', error);
        // Set loading states to false even on error to avoid infinite loading indicator
        setIsLoadingUsers(false);
        setIsLoadingTables(false);
        setIsLoadingStorage(false);
        setIsLoadingFunctions(false);
      }
    };

    fetchData();

  }, [refreshStorageSize]);

  useEffect(() => {
    if (!auth.isAuthenticated) {
      return;
    }

    const unsubscribes: Array<() => void> = [];

    unsubscribes.push(
      registerListener('users_events', (event) => {
        if (!event.data) {
          return;
        }

        console.log('Received user update via ActivityFeedProvider:', event.data);
        getRegularUsersCount()
          .then((count: number) => {
            console.log('Updated user count:', count);
            setUserCount(count);
          })
          .catch((err: unknown) => {
            console.error('Error updating user count:', err);
          });
      })
    );

    unsubscribes.push(
      registerListener('tables_events', (event) => {
        if (!event.data) {
          return;
        }

        console.log('Received table update via ActivityFeedProvider:', event.data);
        getTables()
          .then((tables) => {
            console.log('Updated table count:', tables.length);
            setTableCount(tables.length);
          })
          .catch((err: unknown) => {
            console.error('Error updating table count:', err);
          });

        if (event.data.table === 'files') {
          console.log('File update detected in tables_events, refreshing bucket sizes');
          refreshStorageSize().then(() => {
            console.log('Storage size refresh completed after file update');
          });
        }
      })
    );

    unsubscribes.push(
      registerListener('files_events', (event) => {
        if (!event.data) {
          return;
        }

        console.log('Received file update via ActivityFeedProvider:', event.data);
        refreshStorageSize().then(() => {
          console.log('Storage size refresh completed after file event');
        });
      })
    );

    unsubscribes.push(
      registerListener('buckets_events', (event) => {
        if (!event.data) {
          return;
        }

        console.log('Received bucket update via ActivityFeedProvider:', event.data);
        const relatedBuckets: Array<Record<string, any>> = [];
        if (event.data.new_data) {
          relatedBuckets.push(event.data.new_data);
        }
        if (event.data.old_data) {
          relatedBuckets.push(event.data.old_data);
        }
        if (relatedBuckets.length > 0) {
          primeBucketNames(relatedBuckets);
        }
        console.log('Triggering storage size refresh due to bucket update');
        refreshStorageSize().then(() => {
          console.log('Storage size refresh completed');
        });
      })
    );

    unsubscribes.push(
      registerListener('functions_events', (event) => {
        if (!event.data) {
          return;
        }

        console.log('Received function update via ActivityFeedProvider:', event.data);
        getFunctions()
          .then((functions) => {
            console.log('Updated function count:', functions.total);
            setFunctionCount(functions.total);
          })
          .catch((err: unknown) => {
            console.error('Error updating function count:', err);
          });
      })
    );

    return () => {
      unsubscribes.forEach((unsubscribe) => unsubscribe());
    };
  }, [auth.isAuthenticated, registerListener, refreshStorageSize, primeBucketNames]);

  // Summary card data
  const summaryCards = [
    {
      id: 'users',
      title: 'Users',
      value: isLoadingUsers ? '...' : userCount,
      subtitle: 'Active users'
    },
    {
      id: 'databases',
      title: 'Tables',
      value: isLoadingTables ? '...' : tableCount,
      subtitle: 'Total tables'
    },
    {
      id: 'storage',
      title: 'Storage',
      value: isLoadingStorage ? '...' : formatBytes(storageSize),
      subtitle: 'Used storage'
    },
    {
      id: 'functions',
      title: 'Functions',
      value: isLoadingFunctions ? '...' : functionCount,
      subtitle: 'Deployed functions'
    }
  ];

  // Quick action button data
  const actionButtons = [
    {
      id: 'database-tables',
      title: 'Tables',
      description: 'Manage  tables',
      icon: <TableIcon />,
      onClick: () => navigate('/tables')
    },
    {
      id: 'authentication',
      title: 'Authentication',
      description: 'Manage users & roles',
      icon: <AuthIcon />,
      onClick: () => navigate('/auth')
    },
    {
      id: 'functions',
      title: 'Functions',
      description: 'Deploy functions',
      icon: <FunctionIcon />,
      onClick: () => navigate('/functions')
    },
    {
      id: 'settings',
      title: 'Settings',
      description: 'Manage your profile',
      icon: <SettingsIcon />,
      onClick: () => navigate('/profile')
    }
  ];

  // Client libraries button data
  const clientLibrariesButtons = [
    {
      id: 'api-reference',
      title: 'Rest API',
      description: 'HTTP/REST API documentation',
      icon: <FaCode />,
      onClick: () => navigate('/api-reference'),
      badgeLabel: 'v0.05 · early beta',
      badgeStatus: 'ready' as const
    },
    {
      id: 'swift-sdk',
      title: 'Swift SDK',
      description: 'iOS/macOS client library',
      icon: <FaSwift />,
      onClick: () => window.open('https://github.com/Selfdb-io/selfdb-ios', '_blank', 'noopener,noreferrer'),
      badgeLabel: 'v0.04',
      badgeStatus: 'pending' as const
    },
    {
      id: 'js-sdk',
      title: 'JavaScript SDK',
      description: 'React/Node.js client library',
      icon: <FaReact />,
      onClick: () => window.open('https://github.com/Selfdb-io/js-sdk', '_blank', 'noopener,noreferrer'),
      badgeLabel: 'v0.04',
      badgeStatus: 'pending' as const
    },
    {
      id: 'python-sdk',
      title: 'Python SDK',
      description: 'Python client library',
      icon: <FaPython />,
      onClick: () => window.open('https://github.com/Selfdb-io/selfdb-py', '_blank', 'noopener,noreferrer'),
      badgeLabel: 'v0.04',
      badgeStatus: 'pending' as const
    }
  ];

  return (
    <div className="p-2">

      {/* Summary cards */}
      <SummaryCardGroup cards={summaryCards} />

      <div className="mt-8 grid grid-cols-1 gap-6">
        {/* Quick actions section */}
        <ActionButtonGroup
          title="Quick Actions"
          buttons={actionButtons}
        />

        {/* Client libraries section */}
        <ActionButtonGroup
          title="Client Libraries"
          buttons={clientLibrariesButtons}
          columns={4}
        />

        {/* Recent activity section */}
        <ActivitySection
          title="Live Activity"
          activities={activities}
        />
      </div>
    </div>
  );
};

export default Dashboard;