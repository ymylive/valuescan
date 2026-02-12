import { lazy, Suspense, useEffect } from 'react';
import { Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { Spinner } from '../components/ui';
import { logger } from '../services/loggerService';
import { AdminLayout } from './layouts/AdminLayout';
import { AdminGuard } from '../features/auth/AdminGuard';

const DashboardPage = lazy(() => import('../features/dashboard/DashboardPage'));
const ConfigurationPage = lazy(() => import('../features/configuration/ConfigurationPage'));
const LogsPage = lazy(() => import('../features/logs/LogsPage'));
const ServicesPage = lazy(() => import('../features/services/ServicesPage'));
const ForecastPage = lazy(() => import('../features/forecast/ForecastPage'));
const PublicForecastPage = lazy(() => import('../features/public/PublicForecastPage'));
const AdminLoginPage = lazy(() => import('../features/auth/AdminLoginPage'));

const PageLoader = () => (
  <div className="flex items-center justify-center h-full">
    <Spinner size="lg" />
  </div>
);

export const AppRoutes = () => {
  const location = useLocation();

  useEffect(() => {
    logger.info('router', `Navigated to ${location.pathname}`);
  }, [location.pathname]);

  return (
    <AnimatePresence mode="wait">
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/" element={<PublicForecastPage />} />
          <Route path="/admin/login" element={<AdminLoginPage />} />
          <Route
            path="/admin"
            element={(
              <AdminGuard>
                <AdminLayout />
              </AdminGuard>
            )}
          >
            <Route index element={<DashboardPage />} />
            <Route path="configuration" element={<ConfigurationPage />} />
            <Route path="logs" element={<LogsPage />} />
            <Route path="services" element={<ServicesPage />} />
            <Route path="forecast" element={<ForecastPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </AnimatePresence>
  );
};
