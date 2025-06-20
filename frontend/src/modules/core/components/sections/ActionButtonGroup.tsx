import React from 'react';
import { Card } from '../cards/Card';
import { ActionButton } from '../buttons/ActionButton';

interface ActionButtonData {
  id: string | number;
  title: string;
  description: string;
  icon: React.ReactNode;
  onClick: () => void;
}

interface ActionButtonGroupProps {
  title?: string;
  buttons: ActionButtonData[];
  columns?: 1 | 2 | 3 | 4;
}

export const ActionButtonGroup: React.FC<ActionButtonGroupProps> = ({ 
  title = 'Quick Actions', 
  buttons,
  columns = 2
}) => {
  // Determine grid columns based on prop
  const gridColsClass = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4'
  }[columns];

  return (
    <Card title={title}>
      <div className={`grid ${gridColsClass} gap-4`}>
        {buttons.map((button) => (
          <ActionButton
            key={button.id}
            title={button.title}
            description={button.description}
            icon={button.icon}
            onClick={button.onClick}
          />
        ))}
      </div>
    </Card>
  );
}; 