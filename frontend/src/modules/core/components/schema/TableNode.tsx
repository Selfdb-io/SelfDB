import React from 'react';
import { Handle, Position } from "@xyflow/react";
import { useNavigate } from 'react-router-dom';
import { SchemaNode } from '../../../../services/schemaService';

interface TableNodeProps {
  data: SchemaNode;
}

const TableNode: React.FC<TableNodeProps> = ({ data }) => {
  const navigate = useNavigate();

  const handleTableClick = () => {
    navigate(`/tables/${data.id}`);
  };

  // Determine which columns are foreign keys
  const foreignKeyColumns = data.foreignKeys || [];

  return (
    <div
      className="border-2 border-primary-600 rounded bg-white dark:bg-secondary-800 w-[220px] shadow-md cursor-pointer"
      onClick={handleTableClick}
    >
      {/* Table header */}
      <div className="bg-primary-600 text-white p-2 font-bold text-center rounded-t">
        {data.label}
      </div>

      {/* Table columns */}
      <div className="p-2">
        {data.columns.map((column) => {
          const isPrimaryKey = column.is_primary_key;
          const isForeignKey = foreignKeyColumns.includes(column.column_name);

          return (
            <div
              key={column.column_name}
              className="flex justify-between py-1 border-b border-secondary-100 dark:border-secondary-700 relative"
            >
              <div className={`
                ${isPrimaryKey ? 'text-primary-600 dark:text-primary-400 font-medium' : ''}
                ${isForeignKey ? 'text-accent-500 dark:text-accent-400 font-medium' : 'text-secondary-800 dark:text-secondary-300'}
                text-xs
              `}>
                {isPrimaryKey && '🔑 '}
                {isForeignKey && '🔗 '}
                {column.column_name}
              </div>
              <div className="text-secondary-600 dark:text-secondary-400 text-xs">
                {column.data_type}
              </div>

              {/* Add connection points for foreign keys and primary keys */}
              <Handle
                type={isForeignKey ? "source" : "target"}
                position={isForeignKey ? Position.Right : Position.Left}
                id={column.column_name}
                style={{
                  background: isForeignKey ? 'rgb(20, 184, 166)' : 'rgb(37, 99, 235)',
                  width: 8,
                  height: 8,
                  visibility: isPrimaryKey || isForeignKey ? 'visible' : 'hidden',
                  opacity: isPrimaryKey || isForeignKey ? 1 : 0
                }}
                isConnectable={isPrimaryKey || isForeignKey}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default TableNode; 