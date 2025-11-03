import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { useAuth } from '../context/AuthContext';

export const LoginForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { login, register, error: authError } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      if (isRegistering) {
        // Use the actual register logic from AuthContext
        await register(email, password, firstName, lastName);
        // After successful registration, switch to login mode
        setIsRegistering(false);
      } else {
        // Use the actual login logic from AuthContext
        await login(email, password);
        // After successful login
        navigate('/dashboard');
      }
    } catch (err) {
      // Error is already handled by AuthContext and stored in authError
      // No need to set a generic formError here
    } finally {
      setIsLoading(false);
    }
  };

  // Use auth context error directly
  const error = authError;

  return (
    <div className="w-full max-w-md mx-auto space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold tracking-tight text-secondary-900 dark:text-white">
          {isRegistering ? 'Admin Registration' : 'Admin Login'}
        </h1>
        <p className="text-center text-sm text-secondary-500 dark:text-secondary-400">
          {isRegistering 
            ? 'Create a new admin account for SelfDB' 
            : 'Welcome to the SelfDB! Please enter your details'}
        </p>
      </div>

      {error && (
        <div className="p-3 bg-error-50 border border-error-200 text-error-600 text-sm rounded-md dark:bg-error-900/20 dark:border-error-800 dark:text-error-400">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {isRegistering && (
          <>
            <div className="space-y-2">
              <Label htmlFor="firstName" className="text-sm font-medium text-secondary-700 dark:text-secondary-300">
                First Name
              </Label>
              <Input
                id="firstName"
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
                className="w-full px-3 py-2 border border-secondary-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-secondary-800 dark:border-secondary-600 dark:text-white"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="lastName" className="text-sm font-medium text-secondary-700 dark:text-secondary-300">
                Last Name
              </Label>
              <Input
                id="lastName"
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
                className="w-full px-3 py-2 border border-secondary-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-secondary-800 dark:border-secondary-600 dark:text-white"
              />
            </div>
          </>
        )}
        <div className="space-y-2">
          <Label htmlFor="email" className="text-sm font-medium text-secondary-700 dark:text-secondary-300">
            Email
          </Label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full px-3 py-2 border border-secondary-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-secondary-800 dark:border-secondary-600 dark:text-white"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password" className="text-sm font-medium text-secondary-700 dark:text-secondary-300">
            Password
          </Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full px-3 py-2 border border-secondary-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-secondary-800 dark:border-secondary-600 dark:text-white"
          />
        </div>
        <Button 
          type="submit" 
          disabled={isLoading}
          className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 dark:focus:ring-offset-secondary-900"
        >
          {isLoading ? (
            <span className="flex items-center">
              <span className="h-2 w-2 rounded-full bg-white animate-pulse mr-2"></span>
              {isRegistering ? 'Registering...' : 'Signing in...'}
            </span>
          ) : isRegistering ? (
            'Register'
          ) : (
            'Sign in'
          )}
        </Button>
      </form>
      
    </div>
  );
};