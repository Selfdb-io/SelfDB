import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FaArrowRight } from "react-icons/fa6";
import { ForeignKey } from '../../../../services/tableService';
import { Button } from '../../../../components/ui/button';
import { Table, TableHeader } from '../../../../components/ui/table';

interface TableRelationshipsProps {
  tableName: string;
  foreignKeys?: ForeignKey[];
}

const TableRelationships: React.FC<TableRelationshipsProps> = ({foreignKeys = [] }) => {
  const navigate = useNavigate();

  const handleNavigateToSqlEditor = () => {
    navigate('/sql-editor');
  };

  // Define headers for the table
  const headers: TableHeader[] = [
    { key: 'column', label: 'Column', isSortable: true },
    { key: 'references', label: 'References', isSortable: true },
  ];

  // Render column name cell with styling
  const renderColumn = (columnName: string) => (
    <span className="px-2 py-1 text-xs rounded-full bg-secondary-100 dark:bg-secondary-700 text-secondary-800 dark:text-secondary-200">
      {columnName}
    </span>
  );

  // Render references cell with styling
  const renderReferences = (fk: { foreign_table_name: string; foreign_column_name: string }) => (
    <div className="flex items-center">
      <span className="font-medium text-primary-600 dark:text-primary-400">{fk.foreign_table_name}</span>
      <span className="mx-2 text-secondary-400 dark:text-secondary-500">.</span>
      <span className="px-2 py-1 text-xs rounded-full bg-secondary-100 dark:bg-secondary-700 text-secondary-800 dark:text-secondary-200">
        {fk.foreign_column_name}
      </span>
    </div>
  );

  // Transform foreignKeys data for the Table component
  const tableData = foreignKeys.map(fk => ({
    column: renderColumn(fk.column_name),
    references: renderReferences({
      foreign_table_name: fk.foreign_table_name,
      foreign_column_name: fk.foreign_column_name,
    }),
    // Add original data for sorting if needed (Table component needs raw data for sorting)
    _original: fk 
  }));

  return (
    <div>
      <div className="flex justify-end mb-4">
        <Button
          onClick={handleNavigateToSqlEditor}
          variant="secondary"
          size="sm"
          rightIcon={<FaArrowRight className="w-3 h-3" />}
        >
          Use SQL Editor to add or remove relationship
        </Button>
      </div>
      
      <Table
        headers={headers}
        data={tableData}
        tableClassName="min-w-full"
        // Optional: If sorting is implemented in the Table component, provide a sort function
        // sortFunction={(data, sortKey, sortDirection) => { ... }} 
      />
    </div>
  );
};

export default TableRelationships; 