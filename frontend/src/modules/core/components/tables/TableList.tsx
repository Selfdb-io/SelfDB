import React from 'react';
import { Table as TableData } from '../../../../services/tableService';
import { formatBytes } from '../../utils/formatters';
import { 
  MoreVertical, 
  Database 
} from 'lucide-react';
import { Table, TableHeader } from '../../../../components/ui/table';

interface TableListProps {
  tables: TableData[];
  onTableClick: (tableName: string) => void;
  onTableDeleted?: (tableName: string) => void;
}

// Create an interface for the formatted table data
interface FormattedTableData extends Omit<TableData, 'size' | 'description'> {
  size: string;
  description: string | React.ReactNode | undefined;
}

const TableList: React.FC<TableListProps> = ({ tables, onTableClick }) => {
  const tableHeaders: TableHeader[] = [
    { key: 'name', label: 'Table Name' },
    { key: 'description', label: 'Description' },
    { key: 'column_count', label: 'Columns', isNumeric: true },
    { key: 'size', label: 'Size', isNumeric: true },
  ];

  // Format table data for the reusable Table component
  const formattedData: FormattedTableData[] = tables.map(table => ({
    ...table,
    size: formatBytes(table.size),
    description: table.description || (
      <span className="italic text-secondary-400 dark:text-secondary-500">
        No description
      </span>
    )
  }));

  // Render row icon (database icon)
  const renderRowIcon = () => <Database className="h-5 w-5 text-primary-600" />;

  // Render action buttons - now only the edit action with ellipsis icon
  const renderActions = (item: FormattedTableData) => (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onTableClick(item.name);
      }}
      className="text-secondary-600 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-300"
      aria-label="View table details"
    >
      <MoreVertical className="h-5 w-5" />
    </button>
  );

  // Handle row click
  const handleRowClick = (item: FormattedTableData) => {
    onTableClick(item.name);
  };

  // Custom empty state content
  const EmptyState = () => (
      <div className="bg-white dark:bg-secondary-800 p-8 text-center rounded-lg shadow border border-secondary-200 dark:border-secondary-700">
        <Database className="h-16 w-16 mx-auto text-secondary-400 mb-4" />
        <h3 className="text-lg font-heading font-semibold text-secondary-800 dark:text-secondary-300">
          No tables found in the database
        </h3>
        <p className="mt-2 text-secondary-600 dark:text-secondary-400">
          Create a new table to get started
        </p>
      </div>
    );

  return (
    <>
      {tables.length === 0 ? (
        <EmptyState />
      ) : (
        <Table
          headers={tableHeaders}
          data={formattedData}
          renderRowIcon={renderRowIcon}
          renderActions={renderActions}
          onRowClick={handleRowClick}
        />
      )}
    </>
  );
};

export default TableList; 