import { createContext, useContext, useState, useCallback, useMemo, ReactNode } from 'react'
import { translations, type Language, type TranslationKey } from '../i18n/valuescan'

interface LanguageContextType {
  language: Language
  setLanguage: (lang: Language) => void
  t: (key: TranslationKey) => string
}

const LanguageContext = createContext<LanguageContextType | null>(null)

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    if (typeof window === 'undefined') return 'zh'
    try {
      const saved = localStorage.getItem('valuescan_language')
      return saved === 'en' || saved === 'zh' ? saved : 'zh'
    } catch {
      return 'zh'
    }
  })

  const setLanguage = useCallback((lang: Language) => {
    console.log('[LanguageProvider] Setting language to:', lang)
    setLanguageState(lang)
    try {
      localStorage.setItem('valuescan_language', lang)
    } catch {
      // ignore
    }
  }, [])

  const t = useCallback((key: TranslationKey): string => {
    return translations[language]?.[key] || translations.zh?.[key] || key
  }, [language])

  const value = useMemo(() => ({
    language,
    setLanguage,
    t,
  }), [language, setLanguage, t])

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (!context) {
    // Fallback for components outside provider
    return {
      language: 'zh' as Language,
      setLanguage: () => {},
      t: (key: TranslationKey) => translations.zh?.[key] || key,
    }
  }
  return context
}

export type { Language, TranslationKey }
