import React from 'react'
import '../../styles/minimal.css'

interface MinimalToggleProps {
  checked: boolean
  onChange: () => void
  disabled?: boolean
}

export function MinimalToggle({ checked, onChange, disabled }: MinimalToggleProps) {
  return (
    <div
      className={`minimal-toggle ${checked ? 'active' : ''} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      onClick={disabled ? undefined : onChange}
    >
      <div className="minimal-toggle-dot" />
    </div>
  )
}

interface MinimalFieldProps {
  label: string
  description?: string
  children: React.ReactNode
}

export function MinimalField({ label, description, children }: MinimalFieldProps) {
  return (
    <div className="minimal-field-group">
      <div className="minimal-field-info">
        <div className="minimal-field-title">{label}</div>
        {description && (
          <div className="minimal-field-description">{description}</div>
        )}
      </div>
      <div className="minimal-field-control">{children}</div>
    </div>
  )
}

interface MinimalSectionProps {
  title: string
  children: React.ReactNode
}

export function MinimalSection({ title, children }: MinimalSectionProps) {
  return (
    <div className="minimal-section">
      <div className="minimal-section-title">{title}</div>
      {children}
    </div>
  )
}

interface MinimalInputProps {
  type?: 'text' | 'number' | 'password'
  value: string | number
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  min?: number
  max?: number
  step?: number
}

export function MinimalInput({
  type = 'text',
  value,
  onChange,
  placeholder,
  disabled,
  min,
  max,
  step,
}: MinimalInputProps) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      min={min}
      max={max}
      step={step}
      className="minimal-input"
      style={{ width: type === 'number' ? '120px' : '200px' }}
    />
  )
}

interface MinimalSelectProps {
  value: string
  onChange: (value: string) => void
  options: { value: string; label: string }[]
  disabled?: boolean
}

export function MinimalSelect({
  value,
  onChange,
  options,
  disabled,
}: MinimalSelectProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className="minimal-input"
      style={{ width: '200px' }}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
}
