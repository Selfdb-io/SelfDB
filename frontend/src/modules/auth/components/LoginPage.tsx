import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '../../core/components/Header';
import { Footer } from '../../core/components/Footer';
import { LoginForm } from './LoginForm';
import { useAuth } from '../context/AuthContext';

export const LoginPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  
  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  return (
    <div className="flex flex-col min-h-screen bg-secondary-50 dark:bg-secondary-900 text-secondary-900 dark:text-white">
      <Header />
      
      <main className="flex-1 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-secondary-50 dark:bg-secondary-900">
        <div className="w-full max-w-md bg-white dark:bg-secondary-800 p-8 rounded-lg shadow-sm border border-secondary-100 dark:border-secondary-700">
          <LoginForm />
        </div>
      </main>
      
      <Footer />
    </div>
  );
}; 