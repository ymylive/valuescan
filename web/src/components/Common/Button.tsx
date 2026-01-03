import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

export const Button: React.FC<ButtonProps> = ({ 
  children, 
  className, 
  variant = 'primary', 
  size = 'md', 
  ...props 
}) => {
  const variants = {
    primary: "bg-green-600 hover:bg-green-700 text-white shadow-lg shadow-green-500/20 border border-green-500/50",
    secondary: "bg-white/80 dark:bg-white/10 hover:bg-white dark:hover:bg-white/20 text-gray-900 dark:text-white border border-gray-200 dark:border-white/10",
    danger: "bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/20 border border-red-500/50",
    ghost: "hover:bg-black/5 dark:hover:bg-white/5 text-gray-700 dark:text-gray-300",
  };

  const sizes = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2",
    lg: "px-6 py-3 text-lg",
  };

  return (
    <button
      className={cn(
        "rounded-lg font-medium transition-all duration-200 flex items-center justify-center gap-2",
        "disabled:opacity-50 disabled:cursor-not-allowed backdrop-blur-sm",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
};
