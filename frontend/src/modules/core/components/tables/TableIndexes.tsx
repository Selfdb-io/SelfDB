import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FaArrowRight } from "react-icons/fa6";
import { Index } from '../../../../services/tableService';
import { Table, TableHeader } from '../../../../components/ui/table';
import { Button } from '../../../../components/ui/button';

interface IndexColumn {
  name: string;
}

interface ProcessedIndex {
  name: string;
  is_unique: boolean;
  is_primary: boolean;
  columns: IndexColumn[];
}

interface TableIndexesProps {
  tableName: string;
  indexes?: Index[];
}

const TableIndexes: React.FC<TableIndexesProps> = ({indexes = [] }) => {
  const navigate = useNavigate();

  // Process indexes to group by index_name
  const processedIndexes = React.useMemo<ProcessedIndex[]>(() => {
    const indexMap = new Map<string, ProcessedIndex>();
    
    // Group columns by index name
    indexes.forEach(index => {
      if (!indexMap.has(index.index_name)) {
        indexMap.set(index.index_name, {
          name: index.index_name,
          is_unique: index.is_unique,
          is_primary: index.is_primary,
          columns: []
        });
      }
      
      indexMap.get(index.index_name)?.columns.push({
        name: index.column_name
      });
    });
    
    return Array.from(indexMap.values());
  }, [indexes]);

  const handleNavigateToSqlEditor = () => {
    navigate('/sql-editor');
  };

  // Define headers for the table
  const headers: TableHeader[] = [
    { key: 'indexName', label: 'Index Name', isSortable: true },
    { key: 'type', label: 'Type', isSortable: true },
    { key: 'unique', label: 'Unique', isSortable: true },
    { key: 'columns', label: 'Columns', isSortable: false },
  ];

  // Transform processed indexes to match the format expected by the Table component
  const tableData = processedIndexes.map(index => ({
    indexName: index.name,
    type: index.is_primary ? 'PRIMARY KEY' : 'BTREE',
    unique: index.is_unique ? 'UNIQUE' : 'NON-UNIQUE',
    columns: index.columns,
  }));

  // Render custom type cell with styling
  const renderType = (type: string) => (
    <span className="px-2 py-1 text-xs rounded-full bg-secondary-100 dark:bg-secondary-700 text-secondary-800 dark:text-secondary-200">
      {type}
    </span>
  );

  // Render unique status with appropriate styling
  const renderUnique = (unique: string) => (
    unique === 'UNIQUE' ? (
      <span className="px-2 py-1 text-xs rounded-full bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300">
        UNIQUE
      </span>
    ) : (
      <span className="px-2 py-1 text-xs rounded-full bg-secondary-100 dark:bg-secondary-700 text-secondary-600 dark:text-secondary-300">
        NON-UNIQUE
      </span>
    )
  );

  // Render columns with appropriate styling
  const renderColumns = (columns: IndexColumn[]) => (
    <div className="flex flex-wrap gap-1">
      {Array.isArray(columns) && columns.length > 0 ? (
        columns.map((col: IndexColumn, idx: number) => (
          <div key={idx} className="flex items-center">
            <span className="px-2 py-1 text-xs rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300">
              {col.name}
            </span>
            {idx < columns.length - 1 && <span className="mx-1 text-secondary-400 dark:text-secondary-500">+</span>}
          </div>
        ))
      ) : (
        <span className="text-secondary-400 dark:text-secondary-500 italic">No columns specified</span>
      )}
    </div>
  );

  // Custom render function for each cell
  const customData = tableData.map(item => ({
    ...item,
    type: renderType(item.type),
    unique: renderUnique(item.unique),
    columns: renderColumns(item.columns),
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
          Use SQL Editor to add or remove index
        </Button>
      </div>
      
      <Table
        headers={headers}
        data={customData}
        tableClassName="min-w-full"
      />
    </div>
  );
};

export default TableIndexes; 