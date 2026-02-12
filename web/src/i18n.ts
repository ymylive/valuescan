import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import en from './locales/en.json';
import zh from './locales/zh.json';

const LANGUAGE_STORAGE_KEY = 'valuescan_language';
const SUPPORTED_LANGUAGES = ['en', 'zh'] as const;
type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

const normalizeLanguage = (lang: string | undefined): SupportedLanguage => {
  const base = (lang || '').toLowerCase().split('-')[0];
  return SUPPORTED_LANGUAGES.includes(base as SupportedLanguage) ? (base as SupportedLanguage) : 'en';
};

const persistedLanguage =
  typeof window !== 'undefined' ? window.localStorage.getItem(LANGUAGE_STORAGE_KEY) || undefined : undefined;
const initialLanguage = persistedLanguage ? normalizeLanguage(persistedLanguage) : undefined;

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      zh: { translation: zh },
    },
    ...(initialLanguage ? { lng: initialLanguage } : {}),
    fallbackLng: 'zh',
    supportedLngs: [...SUPPORTED_LANGUAGES],
    nonExplicitSupportedLngs: true,
    load: 'languageOnly',
    returnNull: false,
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: LANGUAGE_STORAGE_KEY,
      caches: ['localStorage'],
    },
    interpolation: {
      escapeValue: false,
    },
  });

i18n.on('languageChanged', (language) => {
  const normalized = normalizeLanguage(language);
  if (typeof document !== 'undefined') {
    document.documentElement.lang = normalized;
  }
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, normalized);
  }
});

export default i18n;
