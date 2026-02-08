import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Theme = 'light' | 'dark';

interface ThemeState {
  theme: Theme;
  isAuto: boolean;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  setIsAuto: (auto: boolean) => void;
}

const applyTheme = (theme: Theme) => {
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
};

const getAutoTheme = (): Theme => {
  const hours = new Date().getHours();
  return hours >= 7 && hours < 19 ? 'light' : 'dark';
};

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: 'dark',
      isAuto: true,

      setTheme: (theme) => {
        applyTheme(theme);
        set({ theme });
      },

      toggleTheme: () => {
        const newTheme = get().theme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
        set({ theme: newTheme, isAuto: false });
      },

      setIsAuto: (auto) => {
        if (auto) {
          const theme = getAutoTheme();
          applyTheme(theme);
          set({ isAuto: true, theme });
        } else {
          set({ isAuto: auto });
        }
      },
    }),
    { name: 'theme-storage' }
  )
);

// Auto theme checker
let intervalId: number | null = null;

export const startAutoThemeChecker = () => {
  if (intervalId) return;

  const check = () => {
    const { isAuto, setTheme } = useThemeStore.getState();
    if (isAuto) {
      setTheme(getAutoTheme());
    }
  };

  check();
  intervalId = window.setInterval(check, 60000);
};

export const stopAutoThemeChecker = () => {
  if (intervalId) {
    clearInterval(intervalId);
    intervalId = null;
  }
};
