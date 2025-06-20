import React from 'react';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  itemName?: string; // e.g., "rows", "files", "users"
}

export const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  totalItems,
  pageSize,
  onPageChange,
  itemName = "items"
}) => {
  const handlePreviousPage = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage + 1);
    }
  };

  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  // Always show pagination info, but only show navigation buttons when there are multiple pages
  const showNavButtons = totalPages > 1;

  return (
    <div className="bg-secondary-50 dark:bg-secondary-800/80 px-6 py-4 border-t border-secondary-200 dark:border-secondary-700 flex items-center justify-between">
      <div className="text-sm text-secondary-700 dark:text-secondary-300 font-sans">
        Showing {itemName} {startItem} to {endItem} of {totalItems}
      </div>
      <div className="flex items-center space-x-3">
        {showNavButtons && (
          <button
            onClick={handlePreviousPage}
            disabled={currentPage === 1}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              currentPage === 1
                ? 'bg-secondary-100 dark:bg-secondary-800 text-secondary-400 dark:text-secondary-600 cursor-not-allowed'
                : 'bg-white dark:bg-secondary-700 text-secondary-800 dark:text-secondary-300 hover:bg-secondary-50 dark:hover:bg-secondary-600 border border-secondary-200 dark:border-secondary-600'
            }`}
          >
            Previous
          </button>
        )}
        <span className="text-sm text-secondary-700 dark:text-secondary-300 font-sans">
          {showNavButtons ? `Page ${currentPage} of ${totalPages}` : `Page 1 of 1`}
        </span>
        {showNavButtons && (
          <button
            onClick={handleNextPage}
            disabled={currentPage === totalPages}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              currentPage === totalPages
                ? 'bg-secondary-100 dark:bg-secondary-800 text-secondary-400 dark:text-secondary-600 cursor-not-allowed'
                : 'bg-white dark:bg-secondary-700 text-secondary-800 dark:text-secondary-300 hover:bg-secondary-50 dark:hover:bg-secondary-600 border border-secondary-200 dark:border-secondary-600'
            }`}
          >
            Next
          </button>
        )}
      </div>
    </div>
  );
}; 