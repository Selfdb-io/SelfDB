import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Header } from './Header';
import { TabBar } from './TabBar';
import { Sidebar } from './Sidebar';
import { Footer } from './Footer';

export interface Tab {
  id: string;
  label: string;
  path: string;
  isClosable: boolean;
}

// Key for storing tabs in localStorage
const TABS_STORAGE_KEY = 'selfdb-tabs';
const ACTIVE_TAB_STORAGE_KEY = 'selfdb-active-tab';

export const MainLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const isClosingTab = useRef(false);
  const currentPathRef = useRef<string>('');
  
  // Load tabs from localStorage or use default Dashboard tab
  const loadSavedTabs = (): Tab[] => {
    try {
      const savedTabs = localStorage.getItem(TABS_STORAGE_KEY);
      if (savedTabs) {
        return JSON.parse(savedTabs);
      }
    } catch (error) {
      console.error('Failed to load tabs from localStorage:', error);
    }
    // Default tab if none are saved
    return [{ id: 'dashboard', label: 'Dashboard', path: '/dashboard', isClosable: false }];
  };
  
  // Load active tab ID from localStorage or use 'dashboard'
  const loadActiveTabId = (): string => {
    try {
      const savedActiveTabId = localStorage.getItem(ACTIVE_TAB_STORAGE_KEY);
      if (savedActiveTabId) {
        return savedActiveTabId;
      }
    } catch (error) {
      console.error('Failed to load active tab from localStorage:', error);
    }
    return 'dashboard';
  };
  
  const [tabs, setTabs] = useState<Tab[]>(loadSavedTabs);
  const [activeTabId, setActiveTabId] = useState<string>(loadActiveTabId);
  const [initialLoadComplete, setInitialLoadComplete] = useState(false);
  
  // Save tabs to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(TABS_STORAGE_KEY, JSON.stringify(tabs));
    } catch (error) {
      console.error('Failed to save tabs to localStorage:', error);
    }
  }, [tabs]);
  
  // Save active tab ID to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem(ACTIVE_TAB_STORAGE_KEY, activeTabId);
    } catch (error) {
      console.error('Failed to save active tab to localStorage:', error);
    }
  }, [activeTabId]);
  
  // Generate tab properties based on the path
  const createTabFromPath = useCallback((path: string): Tab => {
    // Special case for settings/profile
    if (path === '/profile') {
      return { 
        id: 'settings', 
        label: 'Settings', 
        path: '/profile', 
        isClosable: true 
      };
    }
    
    // Handle table-specific routes
    if (path.startsWith('/tables')) {
      // All table operations should use the same tab
      // Tables list, create, view, and edit all share the 'tables' tab
      return {
        id: 'tables',
        label: 'Tables',
        path,
        isClosable: true
      };
    }
    
    // Handle storage-specific routes
    if (path.startsWith('/storage')) {
      // All storage operations should use the same tab
      // Storage list, create, view, and edit all share the 'storage' tab
      return {
        id: 'storage',
        label: 'Storage',
        path,
        isClosable: true
      };
    }
    
    // Handle function-specific routes
    if (path.startsWith('/functions')) {
      // All function operations should use the same tab
      // Functions list, create, view, and edit all share the 'functions' tab
      return {
        id: 'functions',
        label: 'Functions',
        path,
        isClosable: true
      };
    }
    
    // For other paths, create a tab with a capitalized name from the path
    const pathSegments = path.split('/');
    const lastSegment = pathSegments[pathSegments.length - 1] || 'dashboard';
    const label = lastSegment.charAt(0).toUpperCase() + lastSegment.slice(1).replace(/-/g, ' ');
    
    return {
      id: lastSegment, 
      label, 
      path,
      isClosable: lastSegment !== 'dashboard' // Only dashboard is not closable
    };
  }, []);
  
  // Initial setup - make sure the current path has a tab
  useEffect(() => {
    if (initialLoadComplete) return;
    
    const currentPath = location.pathname;
    currentPathRef.current = currentPath;
    
    // Find if the current path already has a tab
    let existingTab: Tab | undefined;
    
    // Special handling for tables - treat all table-related paths as the same tab
    if (currentPath.startsWith('/tables')) {
      existingTab = tabs.find(t => t.id === 'tables');
    } 
    // Special handling for storage - treat all storage-related paths as the same tab
    else if (currentPath.startsWith('/storage')) {
      existingTab = tabs.find(t => t.id === 'storage');
    } 
    // Special handling for functions - treat all function-related paths as the same tab
    else if (currentPath.startsWith('/functions')) {
      existingTab = tabs.find(t => t.id === 'functions');
    }
    else {
      existingTab = tabs.find(t => t.path === currentPath);
    }
    
    if (!existingTab && currentPath !== '/dashboard') {
      // Create a new tab for the current path if it doesn't exist
      const newTab = createTabFromPath(currentPath);
      setTabs(prevTabs => [...prevTabs, newTab]);
      setActiveTabId(newTab.id);
    } else if (existingTab) {
      // If the tab exists, set it as active but update its path if needed
      if (existingTab.id === 'tables' && currentPath.startsWith('/tables')) {
        // For tables tab, update the path while keeping the same tab
        setTabs(prev => 
          prev.map(tab => 
            tab.id === 'tables' ? { ...tab, path: currentPath } : tab
          )
        );
      }
      // For storage tab, update the path while keeping the same tab
      else if (existingTab.id === 'storage' && currentPath.startsWith('/storage')) {
        setTabs(prev => 
          prev.map(tab => 
            tab.id === 'storage' ? { ...tab, path: currentPath } : tab
          )
        );
      }
      // For functions tab, update the path while keeping the same tab
      else if (existingTab.id === 'functions' && currentPath.startsWith('/functions')) {
        setTabs(prev => 
          prev.map(tab => 
            tab.id === 'functions' ? { ...tab, path: currentPath } : tab
          )
        );
      }
      setActiveTabId(existingTab.id);
    }
    
    setInitialLoadComplete(true);
  }, [location.pathname, createTabFromPath, initialLoadComplete]);
  
  // Handle location changes after initial setup
  useEffect(() => {
    if (!initialLoadComplete || isClosingTab.current) return;
    
    const currentPath = location.pathname;
    
    // Skip if path hasn't changed
    if (currentPath === currentPathRef.current) return;
    
    // Update the reference
    currentPathRef.current = currentPath;
    
    // Function to find a tab by its ID
    const findTabById = (id: string) => tabs.find(t => t.id === id);
    
    // Function to find a tab by its path
    const findTabByPath = (path: string) => tabs.find(t => t.path === path);
    
    if (currentPath.startsWith('/tables')) {
      const tablesTab = findTabById('tables');
      
      if (tablesTab) {
        // Update path of existing tables tab and make it active
        if (tablesTab.path !== currentPath) {
          setTabs(prev => 
            prev.map(tab => 
              tab.id === 'tables' ? { ...tab, path: currentPath } : tab
            )
          );
        }
        setActiveTabId('tables');
      } else {
        // Create new tables tab
        const newTab = createTabFromPath(currentPath);
        setTabs(prev => [...prev, newTab]);
        setActiveTabId(newTab.id);
      }
    } 
    // Special handling for storage paths
    else if (currentPath.startsWith('/storage')) {
      const storageTab = findTabById('storage');
      
      if (storageTab) {
        // Update path of existing storage tab and make it active
        if (storageTab.path !== currentPath) {
          setTabs(prev => 
            prev.map(tab => 
              tab.id === 'storage' ? { ...tab, path: currentPath } : tab
            )
          );
        }
        setActiveTabId('storage');
      } else {
        // Create new storage tab
        const newTab = createTabFromPath(currentPath);
        setTabs(prev => [...prev, newTab]);
        setActiveTabId(newTab.id);
      }
    }
    // Special handling for functions paths
    else if (currentPath.startsWith('/functions')) {
      const functionsTab = findTabById('functions');
      
      if (functionsTab) {
        // Update path of existing functions tab and make it active
        if (functionsTab.path !== currentPath) {
          setTabs(prev => 
            prev.map(tab => 
              tab.id === 'functions' ? { ...tab, path: currentPath } : tab
            )
          );
        }
        setActiveTabId('functions');
      } else {
        // Create new functions tab
        const newTab = createTabFromPath(currentPath);
        setTabs(prev => [...prev, newTab]);
        setActiveTabId(newTab.id);
      }
    }
    else {
      const existingTab = findTabByPath(currentPath);
      
      if (existingTab) {
        setActiveTabId(existingTab.id);
      } else {
        const newTab = createTabFromPath(currentPath);
        setTabs(prev => [...prev, newTab]);
        setActiveTabId(newTab.id);
      }
    }
  }, [location.pathname, initialLoadComplete, createTabFromPath]);
  
  const handleTabChange = (tabId: string) => {
    const tab = tabs.find(t => t.id === tabId);
    if (tab) {
      setActiveTabId(tabId);
      navigate(tab.path);
    }
  };
  
  const handleAddTab = (tab: Tab) => {
    // Check if tab with this ID already exists
    const existingTabIndex = tabs.findIndex(t => t.id === tab.id);
    
    if (existingTabIndex >= 0) {
      // If it exists, update its path and activate it
      const updatedTabs = [...tabs];
      updatedTabs[existingTabIndex] = {
        ...updatedTabs[existingTabIndex],
        path: tab.path
      };
      
      setTabs(updatedTabs);
      setActiveTabId(tab.id);
      navigate(tab.path);
      return;
    }
    
    // Otherwise add new tab - set closable true for all except dashboard
    const newTab = {
      ...tab,
      isClosable: tab.id !== 'dashboard' 
    };
    
    setTabs(prev => [...prev, newTab]);
    setActiveTabId(newTab.id);
    navigate(newTab.path);
  };
  
  const handleCloseTab = (tabId: string) => {
    // Set flag to prevent tab recreation in the location effect
    isClosingTab.current = true;
    
    // Don't close if it's the dashboard tab (which should never be closable)
    const tabIndex = tabs.findIndex(t => t.id === tabId);
    if (tabIndex === -1 || tabs[tabIndex].id === 'dashboard') {
      isClosingTab.current = false;
      return;
    }
    
    // Get the tab before removing it
    const tabToClose = tabs[tabIndex];
    
    // Create a new array without the closed tab
    const newTabs = [...tabs.slice(0, tabIndex), ...tabs.slice(tabIndex + 1)];
    setTabs(newTabs);
    
    // If we're closing the active tab, activate the first available tab
    if (tabId === activeTabId) {
      const newActiveTab = newTabs[0];
      setActiveTabId(newActiveTab.id);
      
      // Navigate only if the current path is the one being closed
      if (location.pathname === tabToClose.path) {
        navigate(newActiveTab.path);
      }
    }
    
    // Reset flag after a short delay to allow state updates to complete
    setTimeout(() => {
      isClosingTab.current = false;
    }, 100);
  };

  return (
    <div className="flex flex-col h-screen bg-secondary-100 dark:bg-secondary-900 text-secondary-900 dark:text-white">
      {/* Header - full width */}
      <Header />
      
      {/* Middle section with sidebar and content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <Sidebar onNavigate={handleAddTab} activeTabId={activeTabId} />
        
        {/* Main content area */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Tab bar */}
          <TabBar 
            tabs={tabs} 
            activeTabId={activeTabId} 
            onTabChange={handleTabChange} 
            onCloseTab={handleCloseTab} 
          />
          
          {/* Content area - only allow scrolling when necessary */}
          <main className="flex-1 overflow-auto p-6 bg-white dark:bg-secondary-800 rounded-tl-lg text-base">
            {children}
          </main>
        </div>
      </div>
      
      {/* Footer - full width */}
      <Footer />
    </div>
  );
}; 