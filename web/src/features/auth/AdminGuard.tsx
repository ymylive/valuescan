import { ReactNode, useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spinner } from '../../components/ui';
import { adminCheck } from '../../services/adminAuth';
import { getAdminToken } from '../../services/api';

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
      try {
        const response = await adminCheck();
        if (active) {
          setStatus(response?.success ? 'authed' : 'unauth');
        }
      } catch {
        if (active) {
          setStatus('unauth');
        }
      }
    };

    runCheck();
    return () => {
      active = false;
    };
  }, [location.pathname]);

  if (status === 'checking') {
    return <CheckingState />;
  }

  if (status === 'unauth') {
    return <Navigate to="/admin/login" replace state={{ from: location }} />;
  }

  return <>{children}</>;
};

export default AdminGuard;

