import { useState, useRef, useEffect, memo } from 'react'
import { ChevronDown } from 'lucide-react'

interface ConfigFieldGroupProps {
  title: string
  description?: string
  children: React.ReactNode
  defaultExpanded?: boolean
  icon?: React.ReactNode
  collapsible?: boolean
}

export const ConfigFieldGroup = memo(function ConfigFieldGroup({
  title,
  description,
  children,
  defaultExpanded = true,
  icon,
  collapsible = true,
}: ConfigFieldGroupProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const [height, setHeight] = useState<number | undefined>(undefined)
  const contentRef = useRef<HTMLDivElement>(null)

  // Measure content height for smooth animation
  useEffect(() => {
    if (contentRef.current) {
      setHeight(contentRef.current.scrollHeight)
    }
  }, [children])

  const toggleExpanded = () => {
    if (collapsible) {
      setExpanded(!expanded)
    }
  }

  return (
    <div className="glass-panel rounded-lg overflow-hidden transition-all duration-300 will-change-transform">
      <button
        onClick={toggleExpanded}
        className={`
          w-full flex items-center justify-between p-4
          transition-colors duration-200 text-left
          ${collapsible ? 'hover:bg-white/5 cursor-pointer active:bg-white/10' : 'cursor-default'}
        `}
        type="button"
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-3">
          {icon && (
            <span className="text-neutral-400 transition-colors duration-200">
              {icon}
            </span>
          )}
          <div>
            <h4 className="text-sm font-medium text-white">{title}</h4>
            {description && (
              <p className="text-xs text-neutral-500 mt-0.5">{description}</p>
            )}
          </div>
        </div>
        {collapsible && (
          <div
            className={`
              transition-transform duration-300 ease-out
              will-change-transform
              ${expanded ? 'rotate-180' : 'rotate-0'}
            `}
          >
            <ChevronDown className="w-4 h-4 text-neutral-500" />
          </div>
        )}
      </button>
      <div
        style={{
          maxHeight: expanded ? height : 0,
          transition: 'max-height 300ms cubic-bezier(0.4, 0, 0.2, 1), opacity 200ms ease-out',
        }}
        className={`
          overflow-hidden will-change-[max-height,opacity]
          ${expanded ? 'opacity-100' : 'opacity-0'}
        `}
      >
        <div
          ref={contentRef}
          className="p-4 space-y-4 border-t border-white/5 bg-black/20"
        >
          {children}
        </div>
      </div>
    </div>
  )
})
