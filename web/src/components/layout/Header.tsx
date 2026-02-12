import { useTranslation } from 'react-i18next';
import { Sun, Moon, Globe } from 'lucide-react';
import { useTheme } from '../../hooks';
import { cn } from '../../utils/cn';

export const Header = () => {
  const { t, i18n } = useTranslation();
  const { theme, toggleTheme } = useTheme();

  const iconButtonClass = cn(
    'inline-flex h-10 w-10 items-center justify-center rounded-xl border border-transparent',
    'text-foreground/70 transition hover:border-primary-500/30 hover:bg-primary-500/10 hover:text-primary-700',
    'dark:hover:text-primary-300'
  );

  const toggleLanguage = () => {
    const next = i18n.language.startsWith('zh') ? 'en' : 'zh';
    void i18n.changeLanguage(next);
  };

  const isZh = i18n.language.startsWith('zh');

  return (
    <header className="sticky top-0 z-10 px-0 pt-1 sm:pt-2">
      <div className="shell-panel flex h-16 items-center justify-between rounded-2xl px-4 sm:px-5">
        <div className="min-w-0">
          <h1 className="truncate text-lg font-semibold tracking-tight text-foreground">
            {t('app.title')}
          </h1>
          <p className="hidden text-xs shell-muted-text sm:block">
            {t('app.subtitle')}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={toggleLanguage}
            className={cn(iconButtonClass, 'w-auto gap-1 px-2')}
            title={t('settings.language')}
            aria-label={t('settings.language')}
          >
            <Globe className="h-5 w-5" />
            <span className="text-xs font-semibold uppercase">{isZh ? t('settings.zh') : t('settings.en')}</span>
          </button>

          <button
            onClick={toggleTheme}
            className={iconButtonClass}
            title={t('settings.theme')}
            aria-label={t('settings.theme')}
          >
            {theme === 'dark' ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
