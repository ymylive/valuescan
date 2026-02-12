import { ReactNode, useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spinner } from '../../components/ui';
import { adminCheck } from '../../services/adminAuth';
import { getAdminToken, toApiError } from '../../services/api';

const CheckingState = () => (
  <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-950">
    <Spinner size="lg" />
  </div>
);

export const AdminGuard = ({ children }: { children: ReactNode }) => {
  const location = useLocation();
  const [status, setStatus] = useState<'checking' | 'authed' | 'unauth'>('checking');

  useEffect(() => {
    let active = true;
    const runCheck = async () => {
      const token = getAdminToken();
      if (!token) {
        if (active) {
          setStatus('unauth');
        }
        return;
      }
      if (active) {
        // Keep authenticated view stable while verifying token with backend.
        setStatus('authed');
      }
      try {
        const response = await adminCheck();
        if (active) {
          setStatus(response?.success ? 'authed' : 'unauth');
        }
      } catch (error) {
        if (active && toApiError(error).status === 401) {
          setStatus('unauth');
        }
      }
    };

    runCheck();
    return () => {
      active = false;
    };
  }, []);

  if (status === 'checking') {
    return <CheckingState />;
  }

  if (status === 'unauth') {
    return <Navigate to="/admin/login" replace state={{ from: location }} />;
  }

  return <>{children}</>;
};

export default AdminGuard;

