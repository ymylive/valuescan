import React from 'react';
import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  Sliders,
  Wifi,
  TrendingUp,
  FileText,
  Settings,
  Key,
  X
} from 'lucide-react';
import { cn } from '../Common/GlassCard';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const sidebarVariants = {
  closed: { x: '-100%' },
  open: {
    x: 0,
    transition: {
      type: 'spring',
      stiffness: 300,
      damping: 30
    }
  }
};

const overlayVariants = {
  closed: { opacity: 0 },
  open: { opacity: 1 }
};

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();

  const navItems = [
    { to: '/', icon: LayoutDashboard, label: t('common.dashboard') },
    { to: '/positions', icon: TrendingUp, label: '持仓监控' },
    { to: '/proxy', icon: Wifi, label: '代理节点' },
    { to: '/valuescan-login', icon: Key, label: 'ValuScan 登录' },
    { to: '/logs', icon: FileText, label: '日志监控' },
    { to: '/services', icon: Settings, label: '服务管理' },
    { to: '/configuration', icon: Sliders, label: '系统配置' },
  ];

  return (
    <>
      {/* Mobile Overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial="closed"
            animate="open"
            exit="closed"
            variants={overlayVariants}
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={onClose}
          />
        )}
      </AnimatePresence>

      {/* Sidebar Container */}
      <motion.div
        initial={false}
        animate={isOpen ? 'open' : 'closed'}
        variants={sidebarVariants}
        className={cn(
          "fixed lg:static inset-y-0 left-0 z-50 w-64",
          "bg-white/80 dark:bg-glass-dark/80 glass-effect border-r border-white/20 dark:border-glass-border",
          "lg:translate-x-0 gpu-accelerated"
        )}
      >
        <div className="flex items-center justify-between h-16 px-4 md:px-6 border-b border-white/20 dark:border-glass-border">
          <span className="text-xl md:text-2xl font-bold bg-gradient-to-r from-green-600 to-emerald-400 bg-clip-text text-transparent">
            ValueScan
          </span>
          <button
            onClick={onClose}
            className="lg:hidden p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 smooth-transition touch-manipulation active:scale-95"
            aria-label="Close menu"
          >
            <X size={24} />
          </button>
        </div>

        <nav className="p-4 space-y-2 overflow-y-auto h-[calc(100vh-4rem)]">
          {navItems.map((item, index) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => {
                if (window.innerWidth < 1024) onClose();
              }}
              className={({ isActive }) => cn(
                "flex items-center px-4 py-3 rounded-lg smooth-transition touch-manipulation",
                "text-gray-700 dark:text-gray-300 hover:bg-green-50 dark:hover:bg-white/5",
                "active:scale-98",
                isActive && "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 font-medium shadow-sm"
              )}
              style={{
                animationDelay: `${index * 50}ms`
              }}
            >
              <item.icon size={20} className="mr-3 flex-shrink-0" />
              <span className="truncate">{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </motion.div>
    </>
  );
};
