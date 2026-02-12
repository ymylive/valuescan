import { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';

interface PageContainerProps {
  children: ReactNode;
  className?: string;
}

export const PageContainer = ({ children, className }: PageContainerProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
      className={cn('mx-auto w-full max-w-[1360px] px-3 py-4 sm:px-4 sm:py-5 lg:px-6 lg:py-6', className)}
    >
      {children}
    </motion.div>
  );
};
