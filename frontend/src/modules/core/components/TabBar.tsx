import React from 'react';
import { Tab } from './MainLayout';

interface TabBarProps {
  tabs: Tab[];
  activeTabId: string;
  onTabChange: (tabId: string) => void;
  onCloseTab: (tabId: string) => void;
}

export const TabBar: React.FC<TabBarProps> = ({ 
  tabs, 
  activeTabId, 
  onTabChange, 
  onCloseTab 
}) => {
  return (
    <div className="flex h-10 bg-white dark:bg-secondary-800 border-b border-secondary-100 dark:border-secondary-700">
      <div className="flex overflow-x-auto hide-scrollbar">
        {tabs.map((tab, index) => {
          // Determine if this tab is first or last
          const isFirst = index === 0;
          const isLast = index === tabs.length - 1;
          const isOnly = tabs.length === 1;
          
          // Set border radius based on position
          let borderRadius = '';
          if (isOnly) {
            borderRadius = 'rounded-t-lg';
          } else if (isFirst) {
            borderRadius = 'rounded-tl-lg';
          } else if (isLast) {
            borderRadius = 'rounded-tr-lg';
          }
          
          return (
            <div 
              key={tab.id}
              className={`
                flex items-center h-full min-w-[120px] max-w-[200px] 
                border-r border-secondary-100 dark:border-secondary-700 cursor-pointer relative
                shadow-[inset_0_1px_4px_rgba(0,0,0,0.05)]
                ${borderRadius}
                ${activeTabId === tab.id 
                  ? 'bg-white dark:bg-secondary-800 text-secondary-800 dark:text-white font-medium' 
                  : 'bg-secondary-50 dark:bg-secondary-700 text-secondary-600 dark:text-secondary-300 hover:bg-secondary-100 dark:hover:bg-secondary-600'
                }
              `}
              onClick={() => onTabChange(tab.id)}
            >
              <div className="flex-1 px-4 truncate">{tab.label}</div>
              
              {tab.isClosable && (
                <button 
                  className="h-full px-2 flex items-center justify-center"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCloseTab(tab.id);
                  }}
                >
                  <svg
                    className="h-3 w-3 text-secondary-400 dark:text-secondary-500 hover:text-secondary-700 dark:hover:text-secondary-300 transition-colors"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              )}
              
              {/* Active tab indicator */}
              {activeTabId === tab.id && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-600 dark:bg-primary-400" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Add CSS to hide scrollbar but keep functionality
const style = document.createElement('style');
style.textContent = `
  .hide-scrollbar::-webkit-scrollbar {
    display: none;
  }
  .hide-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
`;
document.head.appendChild(style); 