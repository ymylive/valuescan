import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

interface ConfigFieldGroupProps {
  title: string
  description?: string
  children: React.ReactNode
  defaultExpanded?: boolean
  icon?: React.ReactNode
  collapsible?: boolean
}

export function ConfigFieldGroup({
  title,
  description,
  children,
  defaultExpanded = true,
  icon,
  collapsible = true,
}: ConfigFieldGroupProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)

  return (
    <div className="glass-panel rounded-lg overflow-hidden transition-all duration-300">
      <button
        onClick={() => collapsible && setExpanded(!expanded)}
        className={`w-full flex items-center justify-between p-4 transition-colors text-left ${collapsible ? 'hover:bg-white/5 cursor-pointer' : 'cursor-default'}`}
      >
        <div className="flex items-center gap-3">
          {icon && <span className="text-neutral-400">{icon}</span>}
          <div>
            <h4 className="text-sm font-medium text-white">{title}</h4>
            {description && (
              <p className="text-xs text-neutral-500 mt-0.5">{description}</p>
            )}
          </div>
        </div>
        {collapsible && (
          <div
            className={`transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`}
          >
            <ChevronDown className="w-4 h-4 text-neutral-500" />
          </div>
        )}
      </button>
      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out ${
          expanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="p-4 space-y-4 border-t border-white/5 bg-black/20">
          {children}
        </div>
      </div>
    </div>
  )
}
