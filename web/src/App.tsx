import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { ThemeProvider } from './context/ThemeContext';
import { MainLayout } from './components/Layout/MainLayout';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Traders = lazy(() => import('./pages/Traders'));
const Strategies = lazy(() => import('./pages/Strategies'));
const Models = lazy(() => import('./pages/Models'));
const Exchanges = lazy(() => import('./pages/Exchanges'));
const Debates = lazy(() => import('./pages/Debates'));
const Settings = lazy(() => import('./pages/Settings'));
const ConfigurationPage = lazy(() => import('./pages/ConfigurationPage'));
const ProxyPage = lazy(() => import('./pages/ProxyPage'));

const LoadingSpinner = () => (
  <div className="flex items-center justify-center h-64">
    <motion.div
      className="w-12 h-12 border-4 border-green-500 border-t-transparent rounded-full"
      animate={{ rotate: 360 }}
      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
    />
  </div>
);

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
        <Route path="/traders" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <Traders />
            </Suspense>
          </motion.div>
        } />
        <Route path="/strategies" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <Strategies />
            </Suspense>
          </motion.div>
        } />
        <Route path="/models" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <Models />
            </Suspense>
          </motion.div>
        } />
        <Route path="/exchanges" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <Exchanges />
            </Suspense>
          </motion.div>
        } />
        <Route path="/debates" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <Debates />
            </Suspense>
          </motion.div>
        } />
        <Route path="/settings" element={
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            transition={pageTransition}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <Settings />
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
      </Routes>
    </AnimatePresence>
  );
}

function App() {
  return (
    <ThemeProvider>
      <Router>
        <MainLayout>
          <AnimatedRoutes />
        </MainLayout>
      </Router>
    </ThemeProvider>
  );
}

export default App;