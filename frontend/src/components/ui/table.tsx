'use client';

import React from 'react';
// import { cn } from '@/lib/utils'; // Assuming you have a utility for class names
import { twMerge } from 'tailwind-merge';
import clsx, { ClassValue } from 'clsx';
import { ArrowUp, ArrowDown, ChevronRight, ChevronDown } from 'lucide-react'; // Import icons and Database icon


// Basic cn utility implementation (replace if you have a central one)
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Define the types for the component props
export interface TableHeader {
  key: string;
  label: string;
  isSortable?: boolean;
  isNumeric?: boolean; // For right-aligned numeric columns
}

export interface TableProps<T extends Record<string, any>> {
  headers: TableHeader[];
  data: T[];
  isLoading?: boolean;
  isEmpty?: boolean; // Explicit empty state check
  errorMessage?: string | null; // Allow null for error message
  containerClassName?: string;
  tableClassName?: string;
  // Optional function to render custom content in an actions column
  renderActions?: (item: T) => React.ReactNode;
  // Add action prop for a single action with icon
  action?: {
    icon: React.ReactNode;
    label: string;
    onClick: (item: T) => void;
    disabled?: (item: T) => boolean;
    variant?: 'default' | 'outline' | 'destructive';
  };
  // Optional function to handle sorting
  onSort?: (key: string) => void;
  // Add props for sort state
  sortKey?: string | null;
  sortDirection?: 'asc' | 'desc' | null;
  // Optional function for row click
  onRowClick?: (item: T) => void;
  // Optional function to render an icon for each row
  renderRowIcon?: (item: T) => React.ReactNode;
  // Optional max width for table cells (in characters)
  maxCellWidth?: number;
}

// Reusable Table Component
export function Table<T extends Record<string, any>>({
  headers,
  data,
  isLoading = false,
  isEmpty: explicitEmpty,
  errorMessage,
  containerClassName,
  tableClassName,
  renderActions,
  action,
  onSort,
  sortKey,
  sortDirection,
  onRowClick,
  renderRowIcon,
  maxCellWidth = 94, // Default to ~94 characters
}: TableProps<T>) {
  const hasData = data && data.length > 0;
  const effectiveIsEmpty = explicitEmpty ?? !hasData; // Use explicit prop or infer from data
  
  // State to track expanded cells (using row index + column key)
  const [expandedCells, setExpandedCells] = React.useState<Set<string>>(new Set());

  // Helper function to truncate text and add tooltip
  const truncateText = (content: React.ReactNode, cellId: string, rowIndex: number): React.ReactNode => {
    const expandKey = `${rowIndex}-${cellId}`;
    const isExpanded = expandedCells.has(expandKey);
    
    if (typeof content === 'string') {
      const shouldTruncate = content.length > maxCellWidth;
      
      if (shouldTruncate) {
        const toggleExpansion = () => {
          setExpandedCells(prev => {
            const newSet = new Set(prev);
            if (newSet.has(expandKey)) {
              newSet.delete(expandKey);
            } else {
              newSet.add(expandKey);
            }
            return newSet;
          });
        };

        return (
          <div className="w-full">
            {/* Header row with truncated text and chevron */}
            <div className="flex items-center gap-1">
              <span 
                className="block truncate"
                style={{ maxWidth: `${maxCellWidth}ch` }}
              >
                {content}
              </span>
              <button
                onClick={toggleExpansion}
                className="flex-shrink-0 p-0.5 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded transition-colors"
                title={isExpanded ? "Collapse" : "Expand"}
              >
                {isExpanded ? (
                  <ChevronDown className="h-3 w-3 text-secondary-500" />
                ) : (
                  <ChevronRight className="h-3 w-3 text-secondary-500" />
                )}
              </button>
            </div>
            
            {/* Expandable drawer content */}
            <div 
              className={`overflow-hidden transition-all duration-300 ease-in-out ${
                isExpanded ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
              }`}
            >
              <div className="pt-2 border-t border-secondary-200 dark:border-secondary-600 mt-2">
                <div className="p-3 bg-secondary-50 dark:bg-secondary-900 rounded text-xs leading-relaxed break-words">
                  {content}
                </div>
              </div>
            </div>
          </div>
        );
      }
      return <span className="whitespace-nowrap" style={{ maxWidth: `${maxCellWidth}ch` }}>{content}</span>;
    }
    
    // For non-string content (React elements), just apply max-width
    return <div style={{ maxWidth: `${maxCellWidth}ch` }} className="truncate whitespace-nowrap">{content}</div>;
  };

  // Loading State
  if (isLoading) {
    return (
      <div className={cn(
        "bg-white dark:bg-secondary-800 p-6 rounded-lg shadow border border-secondary-200 dark:border-secondary-700",
        containerClassName
      )}>
        <div className="text-center text-secondary-500 dark:text-secondary-400 py-8 text-base">
          Loading data...
        </div>
      </div>
    );
  }

  // Error State
  if (errorMessage) {
    return (
      <div className={cn(
        "bg-white dark:bg-secondary-800 p-6 rounded-lg shadow border border-secondary-200 dark:border-secondary-700",
        containerClassName
      )}>
        <div className="text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30 p-4 rounded mb-4 text-sm">
          {errorMessage}
        </div>
      </div>
    );
  }

  // Empty State
  if (effectiveIsEmpty && !isLoading) {
    return (
      <div className={cn(
        "bg-white dark:bg-secondary-800 p-8 text-center rounded-lg shadow border border-secondary-200 dark:border-secondary-700",
        containerClassName
      )}>
        
        <h3 className="text-lg font-heading font-semibold text-secondary-800 dark:text-secondary-300">
          No data found
        </h3>
        <p className="mt-2 text-secondary-600 dark:text-secondary-400">
          There are no records to display
        </p>
      </div>
    );
  }

  // Table rendering
  return (
    <div
      className={cn(
        'bg-white dark:bg-secondary-800 rounded-lg shadow border border-secondary-200 dark:border-secondary-700 overflow-x-auto',
        containerClassName
      )}
    >
      <table className={cn('min-w-full divide-y divide-secondary-200 dark:divide-secondary-700', tableClassName)}>
        <thead className="bg-secondary-50 dark:bg-secondary-800">
          <tr>
            {headers.map((header) => (
              <th
                key={header.key}
                scope="col"
                className={cn(
                  'px-6 py-3 text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider',
                  header.key === 'primaryKey' && renderRowIcon ? 'w-10 text-center' : '',
                  header.isNumeric && 'text-right',
                  header.isSortable && 'cursor-pointer hover:bg-secondary-100 dark:hover:bg-secondary-700'
                )}
                onClick={header.isSortable && onSort ? () => onSort(header.key) : undefined}
              >
                {header.isSortable ? (
                  <div className={cn("flex items-center", header.isNumeric && "justify-end")}>
                    <span>{header.label}</span>
                    {/* Add sort indicator icon based on sort state */}
                    {sortKey === header.key && (
                      sortDirection === 'asc' ? (
                        <ArrowUp className="h-3 w-3 ml-1 text-primary-600" />
                      ) : sortDirection === 'desc' ? (
                        <ArrowDown className="h-3 w-3 ml-1 text-primary-600" />
                      ) : null
                    )}
                  </div>
                ) : (
                  header.label
                )}
              </th>
            ))}
            {/* Show action header if action or renderActions is provided */}
            {(renderActions || action) && (
              <th scope="col" className="px-6 py-3 text-center text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                Actions
              </th>
            )}
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-secondary-800 divide-y divide-secondary-200 dark:divide-secondary-700">
          {data.map((item, index) => (
            <tr 
              key={index} 
              className={cn(
                "hover:bg-secondary-50 dark:hover:bg-secondary-700",
                onRowClick && "cursor-pointer"
              )}
              onClick={onRowClick ? () => onRowClick(item) : undefined}
            >
              {headers.map((header, headerIndex) => (
                <td 
                  key={header.key} 
                  className={cn(
                    "text-xs",
                    // Reduce padding for the primary key column with icons
                    header.key === 'primaryKey' && renderRowIcon ? "px-2 py-2 text-center w-10" : "px-6 py-4",
                    headerIndex === 0 && renderRowIcon && header.key !== 'primaryKey' ? "flex items-center" : "",
                    header.isNumeric ? "text-right" : (header.key === 'primaryKey' ? "text-center" : "text-left"),
                    "text-secondary-500 dark:text-secondary-400",
                    // Allow cells to expand vertically when content is expanded
                    "align-top"
                  )}
                >
                  {headerIndex === 0 && renderRowIcon && (
                    <span className={header.key === 'primaryKey' ? "" : "mr-2"}>{renderRowIcon(item)}</span>
                  )}
                  {truncateText(item[header.key] as React.ReactNode, header.key, index)}
                </td>
              ))}
              {/* Render either custom actions or the single action button */}
              {(renderActions || action) && (
                <td className="px-6 py-4 whitespace-nowrap text-center text-xs">
                  <div className="flex justify-center space-x-2">
                    {renderActions ? renderActions(item) : action ? (
                      <button
                        onClick={() => action.onClick(item)}
                        disabled={action.disabled ? action.disabled(item) : false}
                        className={cn(
                          "flex items-center px-3 py-1.5 text-xs rounded-md",
                          "transition duration-200 ease-in-out",
                          action.disabled && action.disabled(item) ? "opacity-50 cursor-not-allowed" : "",
                          action.variant === 'outline' 
                            ? "border border-secondary-300 dark:border-secondary-600 hover:bg-secondary-50 dark:hover:bg-secondary-700" 
                            : action.variant === 'destructive'
                              ? "text-white bg-error-600 hover:bg-error-700 dark:bg-error-700 dark:hover:bg-error-800" 
                              : "text-white bg-primary-600 hover:bg-primary-700 dark:bg-primary-700 dark:hover:bg-primary-800"
                        )}
                      >
                        <span className="mr-1">{action.icon}</span>
                        {action.label}
                      </button>
                    ) : null}
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Example SortIcon component (replace with your actual icon component)
// const SortIcon = ({ direction, active }) => {
//   if (!active) return <span className="ml-1">↕️</span>; // Default icon
//   return <span className="ml-1">{direction === 'asc' ? '🔼' : '🔽'}</span>;
// }; 