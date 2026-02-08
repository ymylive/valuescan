import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export const Input: React.FC<InputProps> = ({ label, className, ...props }) => {
  return (
    <div className="space-y-1">
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          {label}
        </label>
      )}
      <input
        className={cn(
          "w-full px-4 py-2 rounded-lg border focus:ring-2 focus:outline-none transition-all duration-200",
          "bg-white/50 dark:bg-black/20 border-gray-200 dark:border-white/10",
          "focus:ring-green-500/50 focus:border-green-500",
          "text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500",
          className
        )}
        {...props}
      />
    </div>
  );
};
