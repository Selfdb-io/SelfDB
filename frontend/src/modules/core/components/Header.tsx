import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { Button } from '../../../components/ui/button';
import { Sun, Moon, LogOut } from 'lucide-react';

export const Header: React.FC = () => {
  const { isAuthenticated, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  
  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="w-full bg-white dark:bg-secondary-900 border-b border-secondary-100 dark:border-secondary-800">
      <div className="flex justify-between items-center h-16">
        <Link to="/" className="flex items-center h-full pl-4">
          <img src="/logo.svg" alt="SelfDB Logo" className="h-8 w-auto dark:brightness-0 dark:invert" />
          <span className="ml-2 text-xl font-heading font-bold text-secondary-900 dark:text-white">SelfDB</span>
        </Link>
        
        <div className="flex items-center mr-4 space-x-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="rounded-full hover:bg-secondary-100 dark:hover:bg-secondary-800"
            aria-label="Toggle theme"
          >
            {theme === 'light' ? (
              <Moon className="h-5 w-5 text-secondary-800 dark:text-white" />
            ) : (
              <Sun className="h-5 w-5 text-secondary-800 dark:text-white" />
            )}
          </Button>
          
          {isAuthenticated && (
            <Button 
              variant="primary" 
              onClick={handleLogout}
              className="bg-primary-600 text-white hover:bg-primary-700 dark:bg-primary-700 dark:hover:bg-primary-800"
              aria-label="Sign out"
            >
              <LogOut className="h-5 w-5" /> 
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}; 