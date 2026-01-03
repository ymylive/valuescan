import React from 'react';
import { useTranslation } from 'react-i18next';
import { Menu, Moon, Sun, Globe } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { cn } from '../Common/GlassCard';

interface HeaderProps {
  onMenuClick: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onMenuClick }) => {
  const { theme, toggleTheme, isAuto } = useTheme();
  const { i18n } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'zh' : 'en';
    i18n.changeLanguage(newLang);
  };

  return (
    <header className={cn(
      "h-16 px-4 md:px-6 flex items-center justify-between sticky top-0 z-30",
      "bg-white/60 dark:bg-glass-dark/60 glass-effect border-b border-white/20 dark:border-glass-border",
      "gpu-accelerated"
    )}>
      <button
        onClick={onMenuClick}
        className="lg:hidden p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/5 rounded-lg smooth-transition touch-manipulation active:scale-95"
        aria-label="Toggle menu"
      >
        <Menu size={24} />
      </button>

      <div className="flex items-center space-x-2 md:space-x-4 ml-auto">
        <button
          onClick={toggleLanguage}
          className="p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/5 rounded-lg smooth-transition touch-manipulation active:scale-95 flex items-center gap-2"
          title="Switch Language"
          aria-label="Switch Language"
        >
          <Globe size={20} />
          <span className="hidden sm:inline text-sm font-medium uppercase">{i18n.language}</span>
        </button>

        <button
          onClick={toggleTheme}
          className="p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/5 rounded-lg smooth-transition touch-manipulation active:scale-95 relative"
          title={isAuto ? "Auto Mode (Click to toggle manual)" : "Manual Mode"}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Moon size={20} /> : <Sun size={20} />}
          {isAuto && (
            <span className="absolute top-1 right-1 w-2 h-2 bg-green-500 rounded-full ring-2 ring-white dark:ring-gray-900 animate-pulse" />
          )}
        </button>
      </div>
    </header>
  );
};
