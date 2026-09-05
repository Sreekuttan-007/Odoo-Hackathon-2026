import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import type { Role } from '../types';
import { Button } from './ui/Button';

interface ProtectedRouteProps {
  allowedRoles?: Role[];
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-12 text-center">
        <h2 className="text-base font-semibold text-gray-900 mb-1.5">Access Denied</h2>
        <p className="text-sm text-gray-500 mb-5">You don't have access to this area.</p>
        <Button variant="secondary" onClick={() => window.history.back()}>Go Back</Button>
      </div>
    );
  }

  return <Outlet />;
}
