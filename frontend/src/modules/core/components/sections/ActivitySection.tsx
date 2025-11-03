import React from 'react';
import { Card } from '../cards/Card';
import { ActivityItem } from '../activities/ActivityItem';

interface Activity {
  id: string | number;
  title: string;
  description: string;
  timestamp: string;
  icon?: React.ReactNode;
}

interface ActivitySectionProps {
  title?: string;
  activities: Activity[];
}

export const ActivitySection: React.FC<ActivitySectionProps> = ({ 
  title = 'Live Activity', 
  activities 
}) => {
  return (
    <Card title={title}>
      {activities.length > 0 ? (
        <div className="space-y-4 max-h-96 overflow-y-auto pr-1">
          {activities.map((activity) => (
            <ActivityItem
              key={activity.id}
              title={activity.title}
              description={activity.description}
              timestamp={activity.timestamp}
              icon={activity.icon}
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-secondary-500 dark:text-secondary-400">
          No recent activity yet.
        </p>
      )}
    </Card>
  );
}; 