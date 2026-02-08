import { useTranslation } from 'react-i18next';
import { Sun, Moon, Globe } from 'lucide-react';
import { useTheme } from '../../hooks';
import { cn } from '../../utils/cn';

export const Header = () => {
  const { t, i18n } = useTranslation();
  const { theme, toggleTheme } = useTheme();

  const toggleLanguage = () => {
    i18n.changeLanguage(i18n.language === 'zh' ? 'en' : 'zh');
  };

  return (
    <header className="h-16 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between px-6">
      <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
        {t('app.title')}
      </h1>

      <div className="flex items-center gap-2">
        <button
          onClick={toggleLanguage}
          className={cn(
            'p-2 rounded-lg transition-colors',
            'hover:bg-gray-100 dark:hover:bg-gray-800',
            'text-gray-600 dark:text-gray-400'
          )}
          title={t('settings.language')}
        >
          <Globe className="w-5 h-5" />
        </button>

        <button
          onClick={toggleTheme}
          className={cn(
            'p-2 rounded-lg transition-colors',
            'hover:bg-gray-100 dark:hover:bg-gray-800',
            'text-gray-600 dark:text-gray-400'
          )}
          title={t('settings.theme')}
        >
          {theme === 'dark' ? (
            <Sun className="w-5 h-5" />
          ) : (
            <Moon className="w-5 h-5" />
          )}
        </button>
      </div>
    </header>
  );
};
