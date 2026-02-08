import { AnimatePresence, motion } from 'framer-motion';
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react';
import { useToastStore, type Toast as ToastType } from '../../stores';
import { cn } from '../../utils/cn';

const icons = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertCircle,
  info: Info,
};

const ToastItem = ({ toast }: { toast: ToastType }) => {
  const { removeToast } = useToastStore();
  const Icon = icons[toast.type];

  return (
    <motion.div
      initial={{ opacity: 0, y: -20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -20, scale: 0.95 }}
      className={cn(
        'flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg backdrop-blur-sm',
        {
          'bg-green-500/90 text-white': toast.type === 'success',
          'bg-red-500/90 text-white': toast.type === 'error',
          'bg-yellow-500/90 text-white': toast.type === 'warning',
          'bg-blue-500/90 text-white': toast.type === 'info',
        }
      )}
    >
      <Icon className="w-5 h-5 flex-shrink-0" />
      <span className="text-sm font-medium">{toast.message}</span>
      <button onClick={() => removeToast(toast.id)} className="ml-auto p-1 hover:bg-white/20 rounded">
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  );
};

export const ToastContainer = () => {
  const { toasts } = useToastStore();

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
      <AnimatePresence>
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} />
        ))}
      </AnimatePresence>
    </div>
  );
};
