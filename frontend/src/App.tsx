import { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './modules/auth/context/AuthContext';
import { ThemeProvider } from './modules/core/context/ThemeContext';
import { MainLayout } from './modules/core/components/MainLayout';
import { FunctionDetail } from './modules/core/components/functions';
import { Loader } from './modules/core/components/ui/Loader';
import { LoginPage } from './modules/auth/components/LoginPage';

// Lazy load components
const Auth = lazy(() => import('./modules/core/components/pages/Auth'));
const Dashboard = lazy(() => import('./modules/core/components/pages/Dashboard'));
const Profile = lazy(() => import('./modules/settings/components/Settings'));
const Tables = lazy(() => import('./modules/core/components/pages/Tables'));
const TableDetail = lazy(() => import('./modules/core/components/tables/TableDetail'));
const TableEdit = lazy(() => import('./modules/core/components/tables/TableEdit'));
const Storage = lazy(() => import('./modules/core/components/pages/Storage'));
const BucketDetail = lazy(() => import('./modules/core/components/storage/BucketDetail'));
const SqlEditor = lazy(() => import('./modules/core/components/pages/SqlEditor'));
const Functions = lazy(() => import('./modules/core/components/pages/Functions'));
const Schemas = lazy(() => import('./modules/core/components/pages/Schemas'));

// ProtectedRoute component that checks authentication
const ProtectedRoute = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader size="large" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};

// MainLayout wrapper with Suspense
const MainLayoutWrapper = () => (
  <Suspense fallback={
    <div className="flex h-screen items-center justify-center">
      <Loader size="large" />
    </div>
  }>
    <MainLayout>
      <Outlet />
    </MainLayout>
  </Suspense>
);

// Check if user is authenticated and redirect to dashboard if they are
const RedirectIfAuthenticated = () => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader size="large" />
      </div>
    );
  }
  
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return <Outlet />;
};

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Router>
          <Suspense fallback={
            <div className="flex h-screen items-center justify-center">
              <Loader size="large" />
            </div>
          }>
            <Routes>
              {/* Public routes - redirect to dashboard if already authenticated */}
              <Route element={<RedirectIfAuthenticated />}>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<Auth />} />
                <Route path="/forgot-password" element={<Auth />} />
                <Route path="/reset-password" element={<Auth />} />
              </Route>
              
              {/* Protected routes with MainLayout */}
              <Route element={<ProtectedRoute />}>
                <Route element={<MainLayoutWrapper />}>
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/profile" element={<Profile />} />
                  <Route path="/auth" element={<Auth />} />
                  
                  {/* Table routes */}
                  <Route path="/tables" element={<Tables />} />
                  <Route path="/tables/:tableName" element={<TableDetail />} />
                  <Route path="/tables/:tableName/edit" element={<TableEdit />} />
                  
                  {/* Storage routes */}
                  <Route path="/storage" element={<Storage />} />
                  <Route path="/storage/:bucketId" element={<BucketDetail />} />
                  
                  <Route path="/sql-editor" element={<SqlEditor />} />
                  <Route path="/functions" element={<Functions />} />
                  <Route path="/functions/:functionId" element={<FunctionDetail />} />
                  <Route path="/schemas" element={<Schemas />} />
                </Route>
              </Route>
              
              {/* Redirect root to login if not authenticated, dashboard if authenticated */}
              <Route path="/" element={<Navigate to="/login" replace />} />
              <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
          </Suspense>
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
