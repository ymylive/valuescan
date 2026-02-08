import { useThemeStore } from '../stores';

export const useTheme = () => {
  const { theme, isAuto, toggleTheme, setIsAuto } = useThemeStore();
  return { theme, isAuto, toggleTheme, setIsAuto };
};
