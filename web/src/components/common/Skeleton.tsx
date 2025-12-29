import { memo } from 'react'

interface SkeletonProps {
  className?: string
  variant?: 'text' | 'circular' | 'rectangular'
  width?: string | number
  height?: string | number
  animation?: 'pulse' | 'wave' | 'none'
}

/**
 * Skeleton loading component for better UX
 * Memoized to prevent unnecessary re-renders
 */
export const Skeleton = memo(function Skeleton({
  className = '',
  variant = 'text',
  width,
  height,
  animation = 'pulse',
}: SkeletonProps) {
  const baseClasses = 'bg-white/10'

  const variantClasses = {
    text: 'rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-lg',
  }

  const animationClasses = {
    pulse: 'animate-pulse',
    wave: 'animate-shimmer bg-gradient-to-r from-white/5 via-white/10 to-white/5 bg-[length:200%_100%]',
    none: '',
  }

  const style: React.CSSProperties = {}
  if (width) style.width = typeof width === 'number' ? `${width}px` : width
  if (height) style.height = typeof height === 'number' ? `${height}px` : height

  return (
    <div
      className={`
        ${baseClasses}
        ${variantClasses[variant]}
        ${animationClasses[animation]}
        ${className}
      `}
      style={style}
    />
  )
})

/**
 * Config section skeleton loader
 */
export const ConfigSectionSkeleton = memo(function ConfigSectionSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="glass-panel rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-3">
            <Skeleton variant="circular" width={20} height={20} />
            <Skeleton variant="text" width="30%" height={16} />
          </div>
          <div className="space-y-2">
            <Skeleton variant="text" width="100%" height={12} />
            <Skeleton variant="text" width="80%" height={12} />
          </div>
        </div>
      ))}
    </div>
  )
})

/**
 * Service status skeleton loader
 */
export const ServiceStatusSkeleton = memo(function ServiceStatusSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="glass-panel rounded-lg p-6 space-y-4">
          <div className="flex items-center justify-between">
            <Skeleton variant="text" width="40%" height={20} />
            <Skeleton variant="circular" width={24} height={24} />
          </div>
          <div className="space-y-2">
            <Skeleton variant="text" width="60%" height={14} />
            <Skeleton variant="text" width="80%" height={14} />
          </div>
          <div className="flex gap-2">
            <Skeleton variant="rectangular" width={80} height={32} />
            <Skeleton variant="rectangular" width={80} height={32} />
          </div>
        </div>
      ))}
    </div>
  )
})

/**
 * Log viewer skeleton loader
 */
export const LogViewerSkeleton = memo(function LogViewerSkeleton() {
  return (
    <div className="space-y-2">
      {[...Array(15)].map((_, i) => (
        <Skeleton
          key={i}
          variant="text"
          width={`${60 + Math.random() * 40}%`}
          height={16}
        />
      ))}
    </div>
  )
})
