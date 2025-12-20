import { motion, HTMLMotionProps } from 'framer-motion'
import { cn } from '../../lib/utils'

interface GlassCardProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode
  className?: string
  noHover?: boolean
}

export const GlassCard = ({
  children,
  className,
  noHover = false,
  ...props
}: GlassCardProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={
        noHover ? undefined : { scale: 1.01, transition: { duration: 0.2 } }
      }
      className={cn(
        'glass-card bg-neutral-900/30 border border-white/5 p-6 backdrop-blur-sm',
        !noHover && 'hover:border-white/10 hover:bg-neutral-900/40',
        className
      )}
      {...props}
    >
      {children}
    </motion.div>
  )
}
