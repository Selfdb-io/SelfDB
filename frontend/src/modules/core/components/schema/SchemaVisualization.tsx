import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  Edge,
  MarkerType,
  MiniMap,
  Node,
  Panel,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { SchemaData, isSystemTable, loadSchemaLayout, saveSchemaLayout } from '../../../../services/schemaService';
import TableNode from './TableNode';
import { Button } from '../../../../components/ui/button';
import { Download, Save, RefreshCw } from 'lucide-react';

interface SchemaVisualizationProps {
  data: SchemaData;
  onRefresh: () => void;
  isLoading: boolean;
}

// Define your node types at module level, outside of components
const nodeTypesMap = {
  tableNode: TableNode,
};

// Define default edge options outside the component
const defaultEdgeOptionsConfig = {
  type: 'default',
  animated: true,
  style: { stroke: 'rgb(20, 184, 166)', strokeWidth: 2 },
  labelStyle: { display: 'none' },
  label: '',
};

// React Flow component wrapped in provider
const SchemaVisualizationFlow: React.FC<SchemaVisualizationProps> = ({ data, onRefresh, isLoading }) => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const reactFlowInstance = useReactFlow();

  // Initialize nodes and edges states with correct v12 types
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [savedLayout, setSavedLayout] = useState<Record<string, { x: number; y: number }> | null>(null);

  // Load saved layout from localStorage if available
  useEffect(() => {
    const layout = loadSchemaLayout();
    if (layout) {
      setSavedLayout(layout);
    }
  }, []);

  // Transform API data to React Flow format
  useEffect(() => {
    if (!data || !data.nodes || !data.edges) return;

    // Filter tables based on isSystemTable function
    const filteredNodes = data.nodes.filter((node) => {
      return !isSystemTable(node.id);
    });

    // Process foreign key relationships
    const foreignKeyMap: Record<string, string[]> = {};
    data.edges.forEach((edge) => {
      if (!foreignKeyMap[edge.source]) {
        foreignKeyMap[edge.source] = [];
      }
      foreignKeyMap[edge.source].push(edge.source_column);
    });

    // Create nodes with positions
    const flowNodes: Node[] = filteredNodes.map((node, index) => {
      // Check if we have saved positions for this node
      const savedPosition = savedLayout && savedLayout[node.id];

      // Use saved position or default grid layout
      const position = savedPosition || {
        x: 100 + (index % 3) * 300,
        y: 100 + Math.floor(index / 3) * 400,
      };

      return {
        id: node.id,
        type: 'tableNode',
        position,
        data: {
          ...node,
          label: node.label,
          foreignKeys: foreignKeyMap[node.id] || [],
          columns: node.columns.map((col) => ({
            ...col,
            is_primary_key:
              col.column_default?.includes('gen_random_uuid()') ||
              col.column_name === 'id' ||
              (node.primary_keys && node.primary_keys.includes(col.column_name)),
          })),
        },
        draggable: true,
      };
    });

    // Create edges - only include edges where both source and target are in our filtered nodes
    const filteredNodeIds = filteredNodes.map((node) => node.id);
    const flowEdges: Edge[] = data.edges
      .filter(
        (edge) => filteredNodeIds.includes(edge.source) && filteredNodeIds.includes(edge.target)
      )
      .map((edge) => {
        return {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          sourceHandle: edge.source_column, // Connect from the source column
          targetHandle: edge.target_column, // Connect to the target column
          type: 'default',
          animated: true,
          style: { stroke: 'rgb(20, 184, 166)', strokeWidth: 2 },
          label: '',
          labelStyle: { display: 'none' },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: 'rgb(20, 184, 166)',
          },
        };
      });

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [data, savedLayout, setNodes, setEdges]);

  // Save node positions to localStorage
  const saveLayout = useCallback(() => {
    if (!nodes.length) return;

    const positions: Record<string, { x: number; y: number }> = {};
    nodes.forEach((node) => {
      positions[node.id] = { x: node.position.x, y: node.position.y };
    });

    saveSchemaLayout(positions);
    // Show a subtle toast message or UI feedback
    const toast = document.createElement('div');
    toast.className = 'fixed top-4 right-4 bg-success-100 text-success-800 dark:bg-success-900/20 dark:text-success-300 px-4 py-2 rounded shadow';
    toast.textContent = 'Layout saved successfully!';
    document.body.appendChild(toast);
    setTimeout(() => document.body.removeChild(toast), 3000);
  }, [nodes]);

  // Export diagram as PNG
  const exportAsPng = useCallback(() => {
    if (!reactFlowInstance) return;

    // Use reactflow's screenshot functionality instead of toImage
    // This is a workaround since TypeScript doesn't recognize toImage
    // @ts-ignore - toImage is available in reactflow but not in type definitions
    const dataUrl = reactFlowInstance.toImage();
    const link = document.createElement('a');
    link.download = 'schema-diagram.png';
    link.href = dataUrl;
    link.click();
  }, [reactFlowInstance]);

  // Handle React Flow errors
  const handleReactFlowError = (msgId: string, msg: string) => {
    // Suppress the nodeTypes warning (error code 002)
    if (msgId === '002') {
      return;
    }
    console.warn(msg);
  };

  if (!data || !data.nodes || !data.edges) {
    return (
      <div className="flex justify-center items-center h-full">
        <div className="text-secondary-500 dark:text-secondary-400 text-center">
          <p className="mb-2">No schema data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col" ref={reactFlowWrapper}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypesMap}
        onError={handleReactFlowError}
        fitView
        attributionPosition="bottom-right"
        defaultEdgeOptions={defaultEdgeOptionsConfig}
        connectionLineStyle={{ stroke: 'rgb(20, 184, 166)', strokeWidth: 2 }}
        snapToGrid={true}
        snapGrid={[15, 15]}
        className="flex-grow bg-secondary-50 dark:bg-secondary-900"
      >
        <Controls className="bg-white dark:bg-secondary-800 border border-secondary-200 dark:border-secondary-700 rounded" />
        <MiniMap
          nodeStrokeWidth={3}
          zoomable
          pannable
          className="bg-white dark:bg-secondary-800 border border-secondary-200 dark:border-secondary-700 rounded"
        />
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} color="rgb(209 213 219)" />
        <Panel position="top-right">
          <div className="flex gap-2 bg-white dark:bg-secondary-800 p-2 rounded shadow border border-secondary-200 dark:border-secondary-700">
            <Button
              size="sm"
              variant="outline"
              onClick={onRefresh}
              disabled={isLoading}
              leftIcon={<RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />}
            >
              Refresh
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={saveLayout}
              leftIcon={<Save className="h-4 w-4" />}
            >
              Save Layout
            </Button>
            <Button 
              size="sm"
              variant="outline"
              onClick={exportAsPng}
              leftIcon={<Download className="h-4 w-4" />}
            >
              Export PNG
            </Button>
          </div>
        </Panel>
      </ReactFlow>
      <p className="text-xs text-secondary-500 dark:text-secondary-400 text-center p-[5px] min-h-[20px]">
        Tip: Drag tables to organize your schema. Click on a table to view its details.
      </p>
    </div>
  );
};

// Wrap the component with ReactFlowProvider
const SchemaVisualization: React.FC<SchemaVisualizationProps> = ({ data, onRefresh, isLoading }) => {
  return (
    <div className="w-full h-full flex flex-col">
      <ReactFlowProvider>
        <SchemaVisualizationFlow data={data} onRefresh={onRefresh} isLoading={isLoading} />
      </ReactFlowProvider>
    </div>
  );
};

export default SchemaVisualization; 