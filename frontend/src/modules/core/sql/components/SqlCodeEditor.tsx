import React from 'react';

interface SqlCodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

const SqlCodeEditor: React.FC<SqlCodeEditorProps> = ({
  value,
  onChange,
  className = '',
}) => {
  return (
    <div className={`w-full ${className}`}>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full min-h-[250px] bg-secondary-50 dark:bg-secondary-900 text-secondary-800 dark:text-secondary-50 p-4 font-mono text-sm border border-secondary-200 dark:border-secondary-700 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        placeholder="Enter your SQL query here..."
        spellCheck="false"
      />
    </div>
  );
};

export default SqlCodeEditor; 