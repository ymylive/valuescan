import { motion, HTMLMotionProps } from 'framer-motion'
import { ReactNode } from 'react'

// Optimized animation variants with reduced motion support
const prefersReducedMotion = typeof window !== 'undefined' 
  ? window.matchMedia('(prefers-reduced-motion: reduce)').matches 
  : false

export const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: prefersReducedMotion ? 0 : 0.15 },
}

export const slideUp = {
  initial: { opacity: 0, y: prefersReducedMotion ? 0 : 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: prefersReducedMotion ? 0 : -10 },
  transition: { duration: prefersReducedMotion ? 0 : 0.2, ease: 'easeOut' },
}

export const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: prefersReducedMotion ? 0 : 0.03,
    },
  },
}

interface MotionProps extends HTMLMotionProps<'div'> {
  children: ReactNode
  className?: string
  delay?: number
}

export const FadeIn = ({
  children,
  className,
  delay = 0,
  ...props
}: MotionProps) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    transition={{ duration: prefersReducedMotion ? 0 : 0.15, delay: prefersReducedMotion ? 0 : delay }}
    className={className}
    {...props}
  >
    {children}
  </motion.div>
)

export const SlideUp = ({
  children,
  className,
  delay = 0,
  ...props
}: MotionProps) => (
  <motion.div
    initial={{ opacity: 0, y: prefersReducedMotion ? 0 : 12 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: prefersReducedMotion ? 0 : -12 }}
    transition={{ duration: prefersReducedMotion ? 0 : 0.2, delay: prefersReducedMotion ? 0 : delay, ease: 'easeOut' }}
    className={className}
    {...props}
  >
    {children}
  </motion.div>
)

export const ScaleIn = ({
  children,
  className,
  delay = 0,
  ...props
}: MotionProps) => (
  <motion.div
    initial={{ opacity: 0, scale: prefersReducedMotion ? 1 : 0.97 }}
    animate={{ opacity: 1, scale: 1 }}
    exit={{ opacity: 0, scale: prefersReducedMotion ? 1 : 0.97 }}
    transition={{ duration: prefersReducedMotion ? 0 : 0.15, delay: prefersReducedMotion ? 0 : delay }}
    className={className}
    {...props}
  >
    {children}
  </motion.div>
)
