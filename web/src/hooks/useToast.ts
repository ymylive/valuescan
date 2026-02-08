import { useToastStore } from '../stores';

export const useToast = () => {
  const { toasts, addToast, removeToast } = useToastStore();

  return {
    toasts,
    success: (message: string) => addToast('success', message),
    error: (message: string) => addToast('error', message),
    info: (message: string) => addToast('info', message),
    warning: (message: string) => addToast('warning', message),
    remove: removeToast,
  };
};
