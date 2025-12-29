import type { SignalMonitorConfig } from '../../types/config'
import { SignalMonitorConfigSection } from './SignalMonitorConfigSection'

interface AdvancedSignalMonitorConfigSectionProps {
  config: Partial<SignalMonitorConfig>
  onChange: (config: Partial<SignalMonitorConfig>) => void
  errors?: Record<string, string>
}

export function AdvancedSignalMonitorConfigSection({
  config,
  onChange,
  errors,
}: AdvancedSignalMonitorConfigSectionProps) {
  return (
    <SignalMonitorConfigSection
      config={config}
      onChange={onChange}
      errors={errors}
    />
  )
}
