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
  title = 'Recent Activity', 
  activities 
}) => {
  return (
    <Card title={title}>
      <div className="space-y-4">
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
    </Card>
  );
}; 