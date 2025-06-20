import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PlusCircle } from 'lucide-react';
import { FunctionList, FunctionForm } from '../functions';
import { Button } from '../../../../components/ui/button';
import { getFunctions, Function } from '../../../../services/functionService';
import realtimeService from '../../../../services/realtimeService';

const Functions: React.FC = () => {
  const [functions, setFunctions] = useState<Function[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [editFunction, setEditFunction] = useState<Function | null>(null);
  const navigate = useNavigate();

  const fetchFunctions = async () => {
    try {
      setLoading(true);
      const data = await getFunctions();
      setFunctions(data);
      setError(null);
    } catch (err: any) {
      console.error('Error fetching functions:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load functions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFunctions();
    
    const subscriptionId = 'functions';
    realtimeService.subscribe(subscriptionId);
    
    const handleFunctionUpdate = (data: any) => {
      console.log('Received function update via WebSocket:', data);
      fetchFunctions(); // Refetch functions when an update is received
    };
    
    const removeListener = realtimeService.addListener(subscriptionId, handleFunctionUpdate);
    
    const envVarsSubscriptionId = 'function_env_vars';
    realtimeService.subscribe(envVarsSubscriptionId);
    
    const handleEnvVarUpdate = (data: any) => {
      console.log('Received function env var update via WebSocket:', data);
      fetchFunctions(); // Refetch functions when an env var update is received
    };
    
    const removeEnvVarListener = realtimeService.addListener(envVarsSubscriptionId, handleEnvVarUpdate);
    
    return () => {
      removeListener();
      realtimeService.unsubscribe(subscriptionId);
      removeEnvVarListener();
      realtimeService.unsubscribe(envVarsSubscriptionId);
    };
  }, []);

  const handleFunctionClick = (functionId: string) => {
    navigate(`/functions/${functionId}`);
  };

  const handleOpenCreateModal = () => {
    setEditFunction(null);
    setFormModalOpen(true);
  };

  const handleCloseModal = () => {
    setFormModalOpen(false);
    setEditFunction(null);
  };

  const handleEditFunction = (func: Function) => {
    setEditFunction(func);
    setFormModalOpen(true);
  };

  const handleFunctionSuccess = (func: Function) => {
    if (editFunction) {
      setFunctions(prevFunctions => 
        prevFunctions.map(f => f.id === func.id ? func : f)
      );
    } else {
      setFunctions(prevFunctions => [...prevFunctions, func]);
    }
  };

  const handleFunctionDeleted = (id: string) => {
    setFunctions(prevFunctions => prevFunctions.filter(f => f.id !== id));
  };

  return (
    <div className="p-2">
      <div className="flex justify-end mb-4">
        <Button
          onClick={handleOpenCreateModal}
          className="flex items-center"
        >
          <PlusCircle className="mr-2 h-5 w-5" />
          Create Function
        </Button>
      </div>

      <div className="bg-white dark:bg-secondary-800 rounded-lg shadow border border-secondary-200 dark:border-secondary-700">
        <FunctionList
          functions={functions}
          onFunctionClick={handleFunctionClick}
          onEditFunction={handleEditFunction}
          onFunctionDeleted={handleFunctionDeleted}
          loading={loading}
          error={error}
        />
      </div>

      {/* Function Form Modal */}
      <FunctionForm
        isOpen={formModalOpen}
        onClose={handleCloseModal}
        onSuccess={handleFunctionSuccess}
        editFunction={editFunction}
      />
    </div>
  );
};

export default Functions;  