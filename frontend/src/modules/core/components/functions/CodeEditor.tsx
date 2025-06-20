import React from 'react';

interface CodeEditorProps {
  value: string;
  readOnly?: boolean;
  height?: string;
  onChange?: (value: string) => void;
}

const CodeEditor: React.FC<CodeEditorProps> = ({ 
  value, 
  readOnly = false, 
  height = '300px',
  onChange = () => {}
}) => {
  if (readOnly) {
    return (
      <div className="w-full" style={{ height }}>
        <pre className="h-full overflow-auto bg-secondary-50 dark:bg-secondary-900 p-4 text-sm font-mono leading-normal text-secondary-800 dark:text-white rounded-md">
          <code>{value}</code>
        </pre>
      </div>
    );
  }

  return (
    <div className="w-full" style={{ height }}>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-full p-4 font-mono text-sm leading-normal text-secondary-800 dark:text-white bg-secondary-50 dark:bg-secondary-900 border border-secondary-200 dark:border-secondary-700 rounded-md resize-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 outline-none"
        style={{ 
          minHeight: height,
          lineHeight: 1.5,
          tabSize: 2
        }}
        spellCheck={false}
      />
    </div>
  );
};

export default CodeEditor; 