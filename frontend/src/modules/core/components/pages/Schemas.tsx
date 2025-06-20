import React, { useState, useEffect, useCallback } from 'react';
import { fetchSchemaVisualization, SchemaData } from '../../../../services/schemaService';
import { SchemaVisualization } from '../schema';
import { Button } from '../../../../components/ui/button';
import realtimeService from '../../../../services/realtimeService';

const Schemas: React.FC = () => {
  const [schemaData, setSchemaData] = useState<SchemaData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSchema = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchSchemaVisualization();
      setSchemaData(data);
    } catch (err: any) {
      console.error('Error fetching schema:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load schema data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSchema();
    
    const subscriptionId = 'tables';
    realtimeService.subscribe(subscriptionId);
    
    const handleSchemaUpdate = (data: any) => {
      console.log('Received schema update via WebSocket:', data);
      fetchSchema(); // Refetch schema when a table update is received
    };
    
    const removeListener = realtimeService.addListener(subscriptionId, handleSchemaUpdate);
    
    return () => {
      removeListener();
      realtimeService.unsubscribe(subscriptionId);
    };
  }, [fetchSchema]);

  return (
    // Remove fixed height calculation, use flex layout instead
    <div className="flex flex-col flex-grow h-full">
      
      {/* This container must have explicit flex-grow and h-full */}
      <div className="px-4 pb-4 flex-grow h-full">
        <div className="bg-white dark:bg-secondary-800 rounded-lg shadow border border-secondary-100 dark:border-secondary-700 h-full w-full">
          {loading && !schemaData ? (
            <div className="flex justify-center items-center h-full">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
          ) : error ? (
            <div className="p-6 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg text-error-700 dark:text-error-300">
              <h3 className="text-lg font-heading font-semibold mb-2">Error Loading Schema</h3>
              <p>{error}</p>
              <Button
                variant="primary"
                size="sm"
                className="mt-4"
                onClick={fetchSchema}
              >
                Retry
              </Button>
            </div>
          ) : (
            <SchemaVisualization 
              data={schemaData || { nodes: [], edges: [] }} 
              onRefresh={fetchSchema}
              isLoading={loading}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default Schemas;  