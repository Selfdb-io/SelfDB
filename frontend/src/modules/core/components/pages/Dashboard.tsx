import React, { useEffect, useState } from 'react';
import { useAuth } from '../../../auth/context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { SummaryCardGroup, ActionButtonGroup, ActivitySection } from '../sections';
import { TableIcon, AuthIcon, FunctionIcon, SettingsIcon, ClockIcon, DatabaseIcon, UserIcon } from '../icons';
import { getRegularUsersCount } from '../../../../services/userService';
import { getTables } from '../../../../services/tableService';
import { getUserBuckets } from '../../../../services/bucketService';
import { getFunctions } from '../../../../services/functionService';
import realtimeService from '../../../../services/realtimeService';

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
  // Token is not needed here, AuthProvider handles connection
  const auth = useAuth();
  const navigate = useNavigate();
  const [userCount, setUserCount] = useState<number>(0);
  const [tableCount, setTableCount] = useState<number>(0);
  const [storageSize, setStorageSize] = useState<number>(0);
  const [functionCount, setFunctionCount] = useState<number>(0);
  const [isLoadingUsers, setIsLoadingUsers] = useState(true);
  const [isLoadingTables, setIsLoadingTables] = useState(true);
  const [isLoadingStorage, setIsLoadingStorage] = useState(true);
  const [isLoadingFunctions, setIsLoadingFunctions] = useState(true);

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

        // Fetch buckets and calculate total size
        const buckets = await getUserBuckets();
        const totalSize = buckets.reduce((acc, bucket) => acc + bucket.total_size, 0);
        setStorageSize(totalSize);
        setIsLoadingStorage(false);

        // Fetch functions count
        const functions = await getFunctions();
        setFunctionCount(functions.length);
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

  }, []);

  // Define WebSocket handler functions outside of useEffect to avoid recreating them on each render
  const handleUserUpdate = (data: any) => {
    console.log('Received user update via WebSocket:', data);
    // Refresh user count when we receive a database change notification
    getRegularUsersCount().then((count: number) => {
      console.log('Updated user count:', count);
      setUserCount(count);
    }).catch((err: any) => {
      console.error('Error updating user count:', err);
    });
  };

  const handleTableUpdate = (data: any) => {
    console.log('Received table update via WebSocket:', data);
    
    // Always refresh the tables count when we receive any table-related notification
    // This handles both direct table changes and metadata changes
    getTables().then(tables => {
      console.log('Updated table count:', tables.length);
      setTableCount(tables.length);
    }).catch(err => {
      console.error('Error updating table count:', err);
    });
    
    // If the table update is for files, also refresh buckets data
    // This ensures bucket size updates even if direct bucket notifications fail
    if (data.table === 'files') {
      console.log('File update detected, refreshing bucket sizes');
      getUserBuckets().then(buckets => {
        const totalSize = buckets.reduce((acc, bucket) => acc + bucket.total_size, 0);
        console.log('Updated storage size after file operation:', totalSize);
        setStorageSize(totalSize);
      }).catch(err => {
        console.error('Error updating storage size:', err);
      });
    }
  };

  const handleBucketUpdate = (data: any) => {
    console.log('Received bucket update via WebSocket:', data);
    // Always refresh the buckets data when we receive any bucket-related notification
    // This includes both direct bucket changes and file-triggered bucket updates
    getUserBuckets().then(buckets => {
      const totalSize = buckets.reduce((acc, bucket) => acc + bucket.total_size, 0);
      console.log('Updated storage size:', totalSize);
      setStorageSize(totalSize);
    }).catch(err => {
      console.error('Error updating storage size:', err);
    });
  };

  const handleFunctionUpdate = (data: any) => {
    console.log('Received function update via WebSocket:', data);
    // Always refresh the functions count when we receive any function-related notification
    getFunctions().then(functions => {
      console.log('Updated function count:', functions.length);
      setFunctionCount(functions.length);
    }).catch(err => {
      console.error('Error updating function count:', err);
    });
  };

  // Setup WebSocket subscriptions for real-time updates
  useEffect(() => {
    if (!auth.isAuthenticated) return;

    console.log('Setting up WebSocket subscriptions for Dashboard');

    // For users, we directly subscribe to the users_changes channel
    // The getRegularUsers() function queries the 'users' table
    const userSubscriptionId = 'users_changes';
    realtimeService.subscribe(userSubscriptionId);
    const removeUserListener = realtimeService.addListener(userSubscriptionId, handleUserUpdate);

    // For tables, we need to listen to the tables_changes channel
    // The getTables() function queries the database metadata
    // This channel will notify on any table creation/deletion events
    const tableSubscriptionId = 'tables_changes';
    realtimeService.subscribe(tableSubscriptionId);
    const removeTableListener = realtimeService.addListener(tableSubscriptionId, handleTableUpdate);

    // For buckets, we subscribe to the buckets_changes channel
    // The getUserBuckets() function queries the 'buckets' table
    const bucketSubscriptionId = 'buckets_changes';
    realtimeService.subscribe(bucketSubscriptionId);
    const removeBucketListener = realtimeService.addListener(bucketSubscriptionId, handleBucketUpdate);

    // For functions, we subscribe to the functions_changes channel
    // The getFunctions() function queries the 'functions' table
    const functionSubscriptionId = 'functions_changes';
    realtimeService.subscribe(functionSubscriptionId);
    const removeFunctionListener = realtimeService.addListener(functionSubscriptionId, handleFunctionUpdate);

    // Cleanup on component unmount
    return () => {
      console.log('Cleaning up WebSocket subscriptions for Dashboard');
      removeUserListener();
      removeTableListener();
      removeBucketListener();
      removeFunctionListener();

      // Unsubscribe from all channels
      realtimeService.unsubscribe(userSubscriptionId);
      realtimeService.unsubscribe(tableSubscriptionId);
      realtimeService.unsubscribe(bucketSubscriptionId);
      realtimeService.unsubscribe(functionSubscriptionId);
    };
  }, [auth.isAuthenticated]);

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

  // Recent activity data
  const activities = [
    {
      id: 1,
      title: 'Database update',
      description: 'Updated schema in users database',
      timestamp: '2 hours ago',
      icon: <ClockIcon className="w-5 h-5 text-secondary-600 dark:text-secondary-300" />
    },
    {
      id: 2,
      title: 'New user',
      description: 'Added new user to admin group',
      timestamp: '4 hours ago',
      icon: <UserIcon className="w-5 h-5 text-secondary-600 dark:text-secondary-300" />
    },
    {
      id: 3,
      title: 'Function deployed',
      description: 'Deployed new authentication function',
      timestamp: 'Yesterday',
      icon: <FunctionIcon className="w-5 h-5 text-secondary-600 dark:text-secondary-300" />
    },
    {
      id: 4,
      title: 'Database created',
      description: 'Created new analytics database',
      timestamp: '3 days ago',
      icon: <DatabaseIcon className="w-5 h-5 text-secondary-600 dark:text-secondary-300" />
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

        {/* Recent activity section */}
        <ActivitySection
          title="Recent Activity"
          activities={activities}
        />
      </div>
    </div>
  );
};

export default Dashboard;