import { cn } from '../../utils/cn';

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
  className?: string;
}

export const Switch = ({ checked, onChange, label, disabled, className }: SwitchProps) => {
  return (
    <label className={cn('inline-flex items-center cursor-pointer', disabled && 'opacity-50 cursor-not-allowed', className)}>
      <div className="relative">
        <input
          type="checkbox"
          className="sr-only"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
        />
        <div
          className={cn(
            'w-10 h-6 rounded-full transition-colors',
            checked ? 'bg-primary-500' : 'bg-gray-300 dark:bg-gray-600'
          )}
        />
        <div
          className={cn(
            'absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform',
            checked && 'translate-x-4'
          )}
        />
      </div>
      {label && <span className="ml-3 text-sm text-gray-700 dark:text-gray-300">{label}</span>}
    </label>
  );
};
