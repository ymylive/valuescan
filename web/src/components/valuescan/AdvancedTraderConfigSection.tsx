import type { TraderConfig } from '../../types/config'
import { TraderConfigSection } from './TraderConfigSection'

interface AdvancedTraderConfigSectionProps {
  config: Partial<TraderConfig>
  onChange: (config: Partial<TraderConfig>) => void
  errors?: Record<string, string>
}

export function AdvancedTraderConfigSection({
  config,
  onChange,
  errors,
}: AdvancedTraderConfigSectionProps) {
  return (
    <TraderConfigSection config={config} onChange={onChange} errors={errors} />
  )
}
