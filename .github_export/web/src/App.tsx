import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation, useParams } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './components/Common/Toast';
import { MainLayout } from './components/Layout/MainLayout';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const ConfigurationPage = lazy(() => import('./pages/ConfigurationPage'));
const ProxyPage = lazy(() => import('./pages/ProxyPage'));
const PositionMonitor = lazy(() => import('./pages/PositionMonitor'));
const TradingHistory = lazy(() => import('./pages/TradingHistory'));
const PerformanceStats = lazy(() => import('./pages/PerformanceStats'));
const TraderDetails = lazy(() => import('./pages/TraderDetails'));
const LogsPage = lazy(() => import('./pages/LogsPage'));
const ServicesPage = lazy(() => import('./pages/ServicesPage'));
const ValuScanTokenPage = lazy(() => import('./pages/ValuScanTokenPage'));

const LoadingSpinner = () => (
  <div className="flex items-center justify-center h-64">
    <motion.div
      className="w-12 h-12 border-4 border-green-500 border-t-transparent rounded-full"
      animate={{ rotate: 360 }}
      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
    />
  </div>
);

const TraderDetailsWrapper = () => {
  const { traderId } = useParams<{ traderId: string }>();
  return <TraderDetails traderId={traderId || ''} />;
};

const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 }
};

const pageTransition = {
  type: 'tween',
  ease: 'anticipate',
  duration: 0.3
};

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <Dashboard />
            </Suspense>
          </motion.div>
        } />
        <Route path="/configuration" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <ConfigurationPage />
            </Suspense>
          </motion.div>
        } />
        <Route path="/proxy" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <ProxyPage />
            </Suspense>
          </motion.div>
        } />
        <Route path="/positions" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <PositionMonitor />
            </Suspense>
          </motion.div>
        } />
        <Route path="/trading-history" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <TradingHistory />
            </Suspense>
          </motion.div>
        } />
        <Route path="/performance" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <PerformanceStats />
            </Suspense>
          </motion.div>
        } />
        <Route path="/logs" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <LogsPage />
            </Suspense>
          </motion.div>
        } />
        <Route path="/services" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <ServicesPage />
            </Suspense>
          </motion.div>
        } />
        <Route path="/trader/:traderId" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <TraderDetailsWrapper />
            </Suspense>
          </motion.div>
        } />
        <Route path="/valuescan-token" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <ValuScanTokenPage />
            </Suspense>
          </motion.div>
        } />
        <Route path="/valuescan-login" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <ValuScanTokenPage />
            </Suspense>
          </motion.div>
        } />
      </Routes>
    </AnimatePresence>
  );
}

function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <Router>
          <MainLayout>
            <AnimatedRoutes />
          </MainLayout>
        </Router>
      </ToastProvider>
    </ThemeProvider>
  );
}

export default App;
