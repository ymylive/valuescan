import { memo } from 'react'

interface ToggleProps {
  checked: boolean
  onChange: () => void
  disabled?: boolean
  label?: string
  className?: string
}

/**
 * Optimized Toggle component with smooth animations
 * Memoized to prevent unnecessary re-renders
 */
export const Toggle = memo(function Toggle({
  checked,
  onChange,
  disabled = false,
  label,
  className = '',
}: ToggleProps) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <button
        type="button"
        onClick={onChange}
        disabled={disabled}
        className={`
          relative w-10 h-5 rounded-full transition-all duration-300
          border border-white/5 shadow-inner
          ${checked ? 'bg-white' : 'bg-white/10'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          focus:outline-none focus:ring-2 focus:ring-white/20
          will-change-[background-color]
        `}
        aria-checked={checked}
        role="switch"
        aria-label={label || 'Toggle'}
      >
        <span
          className={`
            absolute top-0.5 w-3.5 h-3.5 rounded-full
            transition-all duration-300 shadow-sm
            ${checked ? 'left-5.5 bg-black scale-110' : 'left-1 bg-neutral-500'}
            will-change-[left,transform,background-color]
          `}
        />
      </button>
      {label && (
        <span className="text-sm text-neutral-400 select-none">{label}</span>
      )}
    </div>
  )
})
