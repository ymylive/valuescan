import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  Settings,
  FileText,
  Server,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { cn } from '../../utils/cn';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const navItems = [
  { path: '/admin', icon: LayoutDashboard, labelKey: 'nav.dashboard', end: true },
  { path: '/admin/configuration', icon: Settings, labelKey: 'nav.configuration' },
  { path: '/admin/logs', icon: FileText, labelKey: 'nav.logs' },
  { path: '/admin/services', icon: Server, labelKey: 'nav.services' },
];

export const Sidebar = ({ collapsed, onToggle }: SidebarProps) => {
  const { t } = useTranslation();
  const expandedWidth = 264;
  const collapsedWidth = 72;

  const handleMobileNavClick = () => {
    if (!collapsed && window.innerWidth < 768) {
      onToggle();
    }
  };

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? collapsedWidth : expandedWidth }}
      transition={{ type: 'spring', stiffness: 280, damping: 30 }}
      className="relative z-20 flex h-screen shrink-0 flex-col border-r shell-divider bg-surface/88 backdrop-blur-shell"
    >
      <div className="flex h-16 items-center justify-between border-b shell-divider bg-gradient-to-r from-primary-500/10 to-transparent px-4">
        {!collapsed && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="truncate text-lg font-semibold tracking-tight text-primary-700 dark:text-primary-300"
          >
            Signal
          </motion.span>
        )}
        <button
          onClick={onToggle}
          className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-transparent text-foreground/70 transition hover:border-primary-500/25 hover:bg-primary-500/10 hover:text-primary-700 dark:hover:text-primary-300"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-expanded={!collapsed}
        >
          {collapsed ? (
            <ChevronRight className="h-5 w-5" />
          ) : (
            <ChevronLeft className="h-5 w-5" />
          )}
        </button>
      </div>

      <nav className="flex-1 space-y-1 px-2 py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.end}
            onClick={handleMobileNavClick}
            className={({ isActive }) =>
              cn(
                'group flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors',
                isActive
                  ? 'bg-primary-500/12 text-primary-700 shadow-[inset_0_0_0_1px_rgba(6,182,212,0.3)] dark:text-primary-200'
                  : 'text-foreground/70 hover:bg-surface-muted/75 hover:text-foreground'
              )
            }
          >
            <item.icon className="h-5 w-5 shrink-0" />
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="truncate text-sm font-medium"
              >
                {t(item.labelKey)}
              </motion.span>
            )}
          </NavLink>
        ))}
      </nav>

      {!collapsed && (
        <div className="mx-2 mb-3 rounded-xl border shell-divider bg-surface-muted/70 px-3 py-2 text-xs shell-muted-text">
          Admin Shell
        </div>
      )}
    </motion.aside>
  );
};
