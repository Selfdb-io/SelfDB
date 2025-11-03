import React from 'react';
import ReactMarkdown from 'react-markdown';

import { apiReferenceMarkdown } from '../../constants/apiReferenceMarkdown';

const ApiReference: React.FC = () => {
  return (
    <div className="p-6">
      <div className="max-w-6xl mx-auto">
        <div className="prose prose-lg dark:prose-invert max-w-none">
          <div className="markdown-body bg-white dark:bg-secondary-800 rounded-lg shadow border border-secondary-100 dark:border-secondary-700 p-8">
            <ReactMarkdown
              components={{
                code: ({ node, inline, className, children, ...props }: any) => {
                  if (inline) {
                    return (
                      <code
                        className="bg-secondary-100 dark:bg-secondary-700 px-1.5 py-0.5 rounded text-sm font-mono text-secondary-900 dark:text-secondary-100"
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  }
                  return (
                    <code
                      className={`${className || ''} text-sm font-mono text-secondary-900 dark:text-secondary-100 block`}
                      {...props}
                    >
                      {children}
                    </code>
                  );
                },
                pre: ({ children }: any) => {
                  return (
                    <pre className="bg-secondary-100 dark:bg-secondary-950 rounded-lg p-4 overflow-x-auto mb-4 border border-secondary-300 dark:border-secondary-600">
                      {children}
                    </pre>
                  );
                },
                h1: ({ children }: any) => (
                  <h1 className="text-3xl font-bold mb-6 text-secondary-900 dark:text-white border-b border-secondary-200 dark:border-secondary-700 pb-2">
                    {children}
                  </h1>
                ),
                h2: ({ children }: any) => (
                  <h2 className="text-2xl font-semibold mt-8 mb-4 text-secondary-900 dark:text-white border-b border-secondary-200 dark:border-secondary-700 pb-2">
                    {children}
                  </h2>
                ),
                h3: ({ children }: any) => (
                  <h3 className="text-xl font-semibold mt-6 mb-3 text-secondary-900 dark:text-white">
                    {children}
                  </h3>
                ),
                p: ({ children }: any) => (
                  <p className="mb-4 text-secondary-900 dark:text-secondary-300 leading-relaxed">{children}</p>
                ),
                ul: ({ children }: any) => (
                  <ul className="list-disc list-inside mb-4 text-secondary-900 dark:text-secondary-300 space-y-2">
                    {children}
                  </ul>
                ),
                ol: ({ children }: any) => (
                  <ol className="list-decimal list-inside mb-4 text-secondary-900 dark:text-secondary-300 space-y-2">
                    {children}
                  </ol>
                ),
                li: ({ children }: any) => (
                  <li className="ml-4 text-secondary-900 dark:text-secondary-300">{children}</li>
                ),
                strong: ({ children }: any) => (
                  <strong className="font-semibold text-secondary-900 dark:text-white">{children}</strong>
                ),
                em: ({ children }: any) => (
                  <em className="italic text-secondary-900 dark:text-secondary-300">{children}</em>
                ),
                a: ({ children, href }: any) => (
                  <a
                    href={href}
                    className="text-primary-600 dark:text-primary-400 hover:underline"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {children}
                  </a>
                ),
                blockquote: ({ children }: any) => (
                  <blockquote className="border-l-4 border-primary-500 pl-4 italic my-4 text-secondary-800 dark:text-secondary-400">
                    {children}
                  </blockquote>
                ),
                hr: () => <hr className="my-8 border-secondary-200 dark:border-secondary-700" />,
              }}
            >
              {apiReferenceMarkdown}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ApiReference;

