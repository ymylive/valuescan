import { useState } from 'react'
import { Eye, EyeOff, Copy, Check } from 'lucide-react'

interface SensitiveFieldInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  error?: string
  disabled?: boolean
  fieldKey?: string
  label?: string
}

export function SensitiveFieldInput({
  value,
  onChange,
  placeholder,
  error,
  disabled = false,
  fieldKey: _fieldKey,
  label,
}: SensitiveFieldInputProps) {
  const [visible, setVisible] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (e) {
      console.error('Failed to copy:', e)
    }
  }

  return (
    <div className="space-y-1.5">
      {label && (
        <label className="block text-sm text-neutral-400">{label}</label>
      )}
      <div className="relative group">
        <input
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className={`input-modern pr-20 ${
            error
              ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500/20'
              : ''
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
          <button
            type="button"
            onClick={() => setVisible(!visible)}
            className="p-1.5 text-neutral-500 hover:text-white transition-colors hover:bg-white/10 rounded-md"
            title={visible ? '隐藏' : '显示'}
          >
            {visible ? (
              <EyeOff className="w-4 h-4" />
            ) : (
              <Eye className="w-4 h-4" />
            )}
          </button>
          <button
            type="button"
            onClick={handleCopy}
            disabled={!value}
            className="p-1.5 text-neutral-500 hover:text-white transition-colors hover:bg-white/10 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
            title="复制"
          >
            {copied ? (
              <Check className="w-4 h-4 text-green-500" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  )
}
