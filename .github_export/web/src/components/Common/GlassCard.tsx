import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  animate?: boolean;
  hover?: boolean;
}

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3,
      ease: [0.4, 0, 0.2, 1]
    }
  },
  hover: {
    scale: 1.02,
    transition: {
      duration: 0.2,
      ease: 'easeOut'
    }
  }
};

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className,
  animate = false,
  hover = false,
  ...props
}) => {
  const baseClasses = cn(
    "bg-white/60 dark:bg-glass-dark/50 glass-effect",
    "border border-white/20 dark:border-glass-border",
    "rounded-xl shadow-lg",
    "gpu-accelerated",
    !animate && "smooth-transition",
    className
  );

  if (animate) {
    return (
      <motion.div
        initial="hidden"
        animate="visible"
        variants={cardVariants}
        whileHover={hover ? "hover" : undefined}
        className={baseClasses}
        {...(props as HTMLMotionProps<"div">)}
      >
        {children}
      </motion.div>
    );
  }

  return (
    <div className={baseClasses} {...props}>
      {children}
    </div>
  );
};
