import React from 'react';
import { SummaryCard } from '../cards/SummaryCard';

interface SummaryCardData {
  id: string | number;
  title: string;
  value: string | number;
  subtitle: string;
}

interface SummaryCardGroupProps {
  cards: SummaryCardData[];
  columns?: 1 | 2 | 3 | 4;
}

export const SummaryCardGroup: React.FC<SummaryCardGroupProps> = ({ 
  cards,
  columns = 4
}) => {
  // Determine grid columns based on prop
  const gridColsClass = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-3',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4'
  }[columns];

  return (
    <div className={`grid ${gridColsClass} gap-6`}>
      {cards.map((card) => (
        <SummaryCard
          key={card.id}
          title={card.title}
          value={card.value}
          subtitle={card.subtitle}
        />
      ))}
    </div>
  );
}; 