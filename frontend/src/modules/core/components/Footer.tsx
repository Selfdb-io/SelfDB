import React from 'react';
import { FaGithub } from "react-icons/fa";
import { FaXTwitter } from "react-icons/fa6";
import { FaBook } from "react-icons/fa";
import { SWAGGER_DOCS_URL } from '../../../services/api';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full bg-secondary-50 dark:bg-secondary-900 border-t border-secondary-100 dark:border-secondary-800 py-2">
      <div className="flex flex-col sm:flex-row justify-between items-center px-4">
        <p className="text-secondary-500 dark:text-secondary-400 text-xs">
          &copy; {new Date().getFullYear()} <a href="https://selfdb.io" target="_blank" className="text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">Selfdb.io</a>. All rights reserved.
        </p>
        <div className="flex space-x-3 mt-1 sm:mt-0">
          <a href="https://github.com/Selfdb-io/SelfDB" target="_blank" rel="noreferrer" className="text-secondary-500 hover:text-secondary-800 dark:text-secondary-400 dark:hover:text-white">
            <FaGithub className="w-4 h-4" />
          </a>
          <a href="https://x.com/selfdb_io" target="_blank" rel="noreferrer" className="text-secondary-500 hover:text-secondary-800 dark:text-secondary-400 dark:hover:text-white">
            <FaXTwitter className="w-4 h-4" />
          </a>
          <a href={SWAGGER_DOCS_URL} target="_blank" rel="noreferrer" className="text-secondary-500 hover:text-secondary-800 dark:text-secondary-400 dark:hover:text-white flex items-center">
            <FaBook className="w-4 h-4" />
            <span className="ml-1 text-xs">API</span>
          </a>
        </div>
      </div>
    </footer>
  );
}; 