import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { useAuth } from '../context/AuthContext';


export const LoginForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { login, error: authError } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsLoading(true);

    try {
      // Use the actual login logic from AuthContext
      await login(email, password);
      
      // After successful login
      navigate('/dashboard');
    } catch (err) {
      setFormError('Invalid email or password. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Show either form-specific error or auth context error
  const error = formError || authError;

  return (
    <div className="w-full max-w-md mx-auto space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold tracking-tight text-secondary-900 dark:text-white">Admin Login</h1>
        <p className="text-center text-sm text-secondary-500 dark:text-secondary-400">Welcome to the SelfDB! Please enter your details</p>
      </div>


      {error && (
        <div className="p-3 bg-error-50 border border-error-200 text-error-600 text-sm rounded-md dark:bg-error-900/20 dark:border-error-800 dark:text-error-400">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="name@example.com"
            required
            autoComplete="email"
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>
        
        <div className="pt-2">
          <Button 
            type="submit" 
            className="w-full" 
            disabled={isLoading}
          >
            {isLoading ? 'Signing in...' : 'Sign in'}
          </Button>
        </div>
      </form>

      <div className="text-center text-sm text-secondary-500 dark:text-secondary-400">
        Use the superuser login credentials from your .env file
      </div>
    </div>
  );
}; 