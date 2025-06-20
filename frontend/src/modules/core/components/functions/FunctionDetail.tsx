import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getFunction, deleteFunction, getFunctionVersions, updateFunction, Function } from '../../../../services/functionService';
import { Loader } from '../ui/Loader';
import { Button } from '../../../../components/ui/button';
import { ConfirmationDialog } from '../../../../components/ui/confirmation-dialog';
import { ChevronRight, Pencil, Trash2, Save} from 'lucide-react';
import CodeEditor from './CodeEditor';
import FunctionInfoModal from './FunctionInfoModal';

// Interface for function version from API
interface FunctionVersion {
  id: string;
  function_id: string;
  code: string;
  created_at: string;
  updated_at?: string;
  version_number?: number; // Made optional as it might not always be present
}

// TabPanel component for better tab management
interface TabPanelProps {
  children: React.ReactNode;
  activeTab: number;
  index: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, activeTab, index }) => {
  return (
    <div role="tabpanel" hidden={activeTab !== index} id={`function-tabpanel-${index}`}>
      {activeTab === index && <div className="py-4">{children}</div>}
    </div>
  );
};

// Toggle component for function status
const Toggle: React.FC<{
  isChecked: boolean;
  onChange: (checked: boolean) => void;
  id: string;
}> = ({ isChecked, onChange, id }) => {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={isChecked}
      id={id}
      onClick={() => onChange(!isChecked)}
      className={`
        relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent 
        transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
        ${isChecked ? 'bg-green-600' : 'bg-secondary-200 dark:bg-secondary-700'}
      `}
    >
      <span className="sr-only">{isChecked ? 'On' : 'Off'}</span>
      <span
        aria-hidden="true"
        className={`
          pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow 
          ring-0 transition duration-200 ease-in-out
          ${isChecked ? 'translate-x-4' : 'translate-x-0'}
        `}
      />
    </button>
  );
};

const FunctionDetail: React.FC = () => {
  const { functionId } = useParams<{ functionId: string }>();
  const navigate = useNavigate();
  const [functionData, setFunctionData] = useState<Function | null>(null);
  const [versions, setVersions] = useState<FunctionVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);
  const [isEditingCode, setIsEditingCode] = useState(false);
  const [editedCode, setEditedCode] = useState<string>('');
  const [isSavingCode, setIsSavingCode] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isFunctionInfoModalOpen, setIsFunctionInfoModalOpen] = useState(false);

  useEffect(() => {
    if (!functionId) return;

    const fetchFunctionDetails = async () => {
      try {
        setLoading(true);
        // Fetch function details
        const data = await getFunction(functionId);
        
        // Convert is_active boolean to status string if status is undefined
        if (data.status === undefined && data.is_active !== undefined) {
          data.status = data.is_active ? 'active' : 'draft';
        }
        
        setFunctionData(data);
        setEditedCode(data.code || '');

        // Fetch function versions
        try {
          const versionData = await getFunctionVersions(functionId);
          setVersions(versionData);
        } catch (versionErr: any) {
          console.error('Error fetching versions:', versionErr);
        }

        setError(null);
      } catch (err: any) {
        console.error('Error fetching function details:', err);
        setError(err.response?.data?.detail || err.message || 'Failed to load function details');
      } finally {
        setLoading(false);
      }
    };

    fetchFunctionDetails();
  }, [functionId]);

  const handleTabChange = (tabIndex: number) => {
    setActiveTab(tabIndex);
  };

  const handleDeleteClick = () => {
    setDeleteDialogOpen(true);
    setDeleteError(null);
  };

  const handleDeleteConfirm = async () => {
    if (!functionId) return;

    setIsDeleting(true);
    setDeleteError(null);

    try {
      await deleteFunction(functionId);
      // Navigate back to functions list after successful deletion
      navigate('/functions');
    } catch (err: any) {
      console.error('Error deleting function:', err);
      setDeleteError(err.response?.data?.detail || err.message || 'Failed to delete function');
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setDeleteError(null);
  };

  const handleCodeChange = (newCode: string) => {
    setEditedCode(newCode);
  };

  const handleToggleEditCode = () => {
    if (isEditingCode && functionData) {
      // Cancel editing, reset to original code
      setEditedCode(functionData.code || '');
    }
    setIsEditingCode(!isEditingCode);
    setSaveError(null);
  };

  const handleSaveCode = async () => {
    if (!functionId || !functionData) return;

    setIsSavingCode(true);
    setSaveError(null);

    try {
      const updatedFunction = await updateFunction(functionId, {
        ...functionData,
        code: editedCode
      });

      // Update the function data
      setFunctionData(updatedFunction);
      
      // Refresh versions
      const versionData = await getFunctionVersions(functionId);
      setVersions(versionData);
      
      // Exit edit mode
      setIsEditingCode(false);
    } catch (err: any) {
      console.error('Error saving function code:', err);
      setSaveError(err.response?.data?.detail || err.message || 'Failed to save function code');
    } finally {
      setIsSavingCode(false);
    }
  };

  // Function to display differences between versions
  const getDiffDisplay = (oldCode: string, newCode: string) => {
    if (!oldCode || !newCode) return 'Cannot compare versions';

    // Simple line-by-line diff
    const oldLines = oldCode.split('\n');
    const newLines = newCode.split('\n');
    const maxLines = Math.max(oldLines.length, newLines.length);
    let diffOutput = '';

    for (let i = 0; i < maxLines; i++) {
      const oldLine = i < oldLines.length ? oldLines[i] : null;
      const newLine = i < newLines.length ? newLines[i] : null;

      if (oldLine === null) {
        // Line added
        diffOutput += `+ ${newLine}\n`;
      } else if (newLine === null) {
        // Line removed
        diffOutput += `- ${oldLine}\n`;
      } else if (oldLine !== newLine) {
        // Line changed
        diffOutput += `- ${oldLine}\n+ ${newLine}\n`;
      } else {
        // Line unchanged
        diffOutput += `  ${newLine}\n`;
      }
    }

    return diffOutput;
  };

  const handleFunctionInfoUpdate = () => {
    // Refresh function data after update
    if (functionId) {
      getFunction(functionId)
        .then(data => {
          // Convert is_active boolean to status string if status is undefined
          if (data.status === undefined && data.is_active !== undefined) {
            data.status = data.is_active ? 'active' : 'draft';
          }
          
          setFunctionData(data);
        })
        .catch(err => {
          console.error('Error refreshing function details:', err);
        });
    }
  };

  if (loading) {
    return (
      <div className="p-2">
        <div className="flex items-center mb-4">
          <button
            onClick={() => navigate('/functions')}
            className="mr-4 text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 font-medium"
          >
            ← Back to Functions
          </button>
          <h2 className="text-2xl font-heading font-semibold text-secondary-800 dark:text-white tracking-tight">
            Loading Function
          </h2>
        </div>
        <div className="bg-white dark:bg-secondary-800 p-12 rounded-lg shadow border border-secondary-200 dark:border-secondary-700 flex justify-center">
          <Loader size="large" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-2">
        <div className="flex items-center mb-4">
          <button
            onClick={() => navigate('/functions')}
            className="mr-4 text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 font-medium"
          >
            ← Back to Functions
          </button>
          <h2 className="text-2xl font-heading font-semibold text-secondary-800 dark:text-white tracking-tight">
            Error Loading Function
          </h2>
        </div>
        <div className="bg-error-50 dark:bg-error-900/20 p-6 rounded-lg border border-error-200 dark:border-error-800 text-error-700 dark:text-error-300">
          <h3 className="text-lg font-heading font-semibold mb-2">Error</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!functionData || !functionId) {
    return (
      <div className="p-2">
        <div className="bg-error-50 dark:bg-error-900/20 p-6 rounded-lg border border-error-200 dark:border-error-800 text-error-700 dark:text-error-300">
          <h3 className="text-lg font-heading font-semibold mb-2">Error</h3>
          <p>Function not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-2">
      {/* Breadcrumbs */}
      <nav className="flex items-center text-sm text-secondary-500 dark:text-secondary-400 mb-4">
        <Link to="/functions" className="hover:text-primary-600 dark:hover:text-primary-400">
          Functions
        </Link>
        <ChevronRight className="w-4 h-4 mx-2" />
        <span className="text-secondary-800 dark:text-white">{functionData.name}</span>
      </nav>

      {/* Header */}
      <div className="flex items-center mb-4">
        <div className="flex items-baseline flex-1 mr-4">
          <h2 className="text-2xl font-heading font-semibold text-secondary-800 dark:text-white tracking-tight">
            {functionData.name}
          </h2>
          <div className="flex items-center ml-3">
            <div className="flex items-center">
              <Toggle
                id={`function-toggle-${functionId}`}
                isChecked={functionData.status === 'active'}
                onChange={async (checked) => {
                  try {
                    // Update function status
                    const updatePayload: Partial<Function> = {
                      is_active: checked,
                      status: checked ? 'active' : 'draft'
                    };
                    
                    await updateFunction(functionId, updatePayload);
                    
                    // Update local state
                    setFunctionData({
                      ...functionData,
                      status: checked ? 'active' : 'draft',
                      is_active: checked
                    });
                  } catch (err) {
                    console.error('Error updating function status:', err);
                  }
                }}
              />
              <span className="ml-2 text-xs font-medium text-secondary-600 dark:text-secondary-400">
                {functionData.status === 'active' ? 'On' : 'Off'}
              </span>
            </div>
            {functionData.description && (
              <span className="ml-2 italic text-sm text-secondary-600 dark:text-secondary-400">
                {functionData.description}
              </span>
            )}
            <button
              onClick={() => setIsFunctionInfoModalOpen(true)}
              className="ml-2 p-1 text-secondary-400 hover:text-secondary-600 dark:hover:text-secondary-300 transition-colors"
              title="Edit function information"
            >
              <Pencil className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={handleDeleteClick}
            className="p-2 rounded-md text-error-600 dark:text-error-400 border border-error-300 dark:border-error-500 hover:bg-error-50 dark:hover:bg-error-900/30 transition-colors"
            aria-label="Delete function"
            title="Delete function"
          >
            <Trash2 className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="mb-6 border-b border-secondary-200 dark:border-secondary-700">
        <div className="flex space-x-1 overflow-x-auto">
          <button
            onClick={() => handleTabChange(0)}
            className={`px-4 py-2 font-medium text-sm focus:outline-none ${
              activeTab === 0
                ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
                : 'text-secondary-600 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-300'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => handleTabChange(1)}
            className={`px-4 py-2 font-medium text-sm focus:outline-none ${
              activeTab === 1
                ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
                : 'text-secondary-600 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-300'
            }`}
          >
            Code
          </button>
          <button
            onClick={() => handleTabChange(2)}
            className={`px-4 py-2 font-medium text-sm focus:outline-none ${
              activeTab === 2
                ? 'border-b-2 border-primary-500 text-primary-600 dark:text-primary-400'
                : 'text-secondary-600 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-300'
            }`}
          >
            Versions
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="bg-white dark:bg-secondary-800 rounded-lg shadow border border-secondary-200 dark:border-secondary-700">
        <TabPanel activeTab={activeTab} index={0}>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-lg font-semibold mb-4 text-secondary-800 dark:text-white">Function Details</h3>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium text-secondary-500 dark:text-secondary-400">HTTP Endpoint</p>
                    <p className="mt-1 font-mono bg-secondary-50 dark:bg-secondary-900 p-2 rounded text-secondary-800 dark:text-white">
                      /{functionData.name.toLowerCase()}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Trigger Type</p>
                    <p className="mt-1">{functionData.trigger_type || 'HTTP'}</p>
                  </div>
                </div>
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-4 text-secondary-800 dark:text-white">Status</h3>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Status</p>
                    <div className="mt-1">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                        ${functionData.status === 'active' 
                          ? 'bg-success-100 dark:bg-success-900/20 text-success-800 dark:text-success-300' 
                          : 'bg-warning-100 dark:bg-warning-900/20 text-warning-800 dark:text-warning-300'}`}
                      >
                        {functionData.status === 'active' ? 'On' : 'Off'}
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Created</p>
                    <p className="mt-1">{new Date(functionData.created_at).toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Last Updated</p>
                    <p className="mt-1">{new Date(functionData.updated_at).toLocaleString()}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </TabPanel>

        <TabPanel activeTab={activeTab} index={1}>
          <div className="p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-secondary-800 dark:text-white">Function Code</h3>
              <div className="flex space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleToggleEditCode}
                >
                  {isEditingCode ? 'Cancel' : 'Edit Code'}
                </Button>
                {isEditingCode && (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleSaveCode}
                    disabled={isSavingCode}
                    className="flex items-center"
                  >
                    {isSavingCode ? (
                      <>
                        <Loader size="small" className="mr-2" /> Saving...
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4 mr-2" /> Save Changes
                      </>
                    )}
                  </Button>
                )}
              </div>
            </div>
            
            {saveError && (
              <div className="mb-4 p-4 bg-error-100 dark:bg-error-900/20 text-error-700 dark:text-error-300 rounded-md text-sm">
                {saveError}
              </div>
            )}

            <div className="border border-secondary-200 dark:border-secondary-700 rounded-lg overflow-hidden">
              <CodeEditor 
                value={isEditingCode ? editedCode : functionData.code || '// No code available'} 
                readOnly={!isEditingCode}
                height="400px"
                onChange={handleCodeChange}
              />
            </div>
          </div>
        </TabPanel>

        <TabPanel activeTab={activeTab} index={2}>
          <div className="p-6">
            <h3 className="text-lg font-semibold mb-4 text-secondary-800 dark:text-white">Version History</h3>
            
            {versions && versions.length > 0 ? (
              <div className="space-y-4">
                {versions.map((version, index) => (
                  <div key={version.id} className="border border-secondary-200 dark:border-secondary-700 rounded-lg p-4">
                    <div className="flex justify-between items-center mb-3">
                      <div>
                        <h4 className="font-medium text-secondary-800 dark:text-white">
                          Version {version.version_number || index + 1}
                        </h4>
                        <p className="text-sm text-secondary-500 dark:text-secondary-400">
                          Created: {new Date(version.created_at).toLocaleString()}
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedVersion(version.id === selectedVersion ? null : version.id)}
                      >
                        {version.id === selectedVersion ? 'Hide Code' : 'View Code'}
                      </Button>
                    </div>

                    {version.id === selectedVersion && (
                      <div className="mt-4">
                        <div className="border border-secondary-200 dark:border-secondary-700 rounded-lg overflow-hidden">
                          <CodeEditor 
                            value={version.code || '// No code available'} 
                            readOnly={true} 
                            height="300px" 
                          />
                        </div>

                        {index < versions.length - 1 && (
                          <div className="mt-4 bg-secondary-50 dark:bg-secondary-900 p-4 rounded-lg">
                            <h5 className="font-medium mb-2 text-secondary-800 dark:text-white">Changes from previous version</h5>
                            <div className="font-mono text-sm whitespace-pre-wrap bg-white dark:bg-secondary-800 p-3 rounded border border-secondary-200 dark:border-secondary-700 overflow-auto max-h-64">
                              {getDiffDisplay(versions[index + 1].code, version.code)}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-secondary-500 dark:text-secondary-400 py-4">
                No version history available. Version history is created each time you update this function.
              </div>
            )}
          </div>
        </TabPanel>
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={deleteDialogOpen}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Delete Function"
        description={
          <>
            <p className="text-secondary-600 dark:text-secondary-300">
              Are you sure you want to delete the function "{functionData.name}"? This action cannot be undone.
            </p>
            
            {deleteError && (
              <div className="mt-3 p-2 bg-error-100 dark:bg-error-900 text-error-700 dark:text-error-300 rounded-md text-sm">
                {deleteError}
              </div>
            )}
          </>
        }
        confirmButtonText={isDeleting ? "Deleting..." : "Delete"}
        isDestructive={true}
        isConfirmLoading={isDeleting}
      />

      {/* Add the FunctionInfoModal at the end of the component */}
      {functionId && functionData && (
        <FunctionInfoModal
          isOpen={isFunctionInfoModalOpen}
          onClose={() => setIsFunctionInfoModalOpen(false)}
          functionId={functionId}
          functionName={functionData.name}
          functionDescription={functionData.description}
          functionStatus={functionData.status}
          onUpdate={handleFunctionInfoUpdate}
        />
      )}
    </div>
  );
};

export default FunctionDetail; 