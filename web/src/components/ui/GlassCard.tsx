import { cn } from '../../lib/utils'

interface GlassCardProps {
  children: React.ReactNode
  className?: string
  noHover?: boolean
}

// Optimized: Removed framer-motion for better performance, using CSS transitions instead
export const GlassCard = ({
  children,
  className,
  noHover = false,
}: GlassCardProps) => {
  return (
    <div
      className={cn(
        'glass-card bg-neutral-900/30 border border-white/5 p-6',
        !noHover && 'hover:border-white/10 hover:bg-neutral-900/40',
        className
      )}
    >
      {children}
    </div>
  )
}
