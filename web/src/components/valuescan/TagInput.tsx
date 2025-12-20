import { useState, KeyboardEvent } from 'react'
import { X } from 'lucide-react'

interface TagInputProps {
  tags: string[]
  onChange: (tags: string[]) => void
  placeholder?: string
  label?: string
  description?: string
}

/**
 * Parse comma-separated string into array of trimmed non-empty values
 */
export function parseCommaSeparated(input: string): string[] {
  return input
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
}

/**
 * Convert array to comma-separated string
 */
export function toCommaSeparated(tags: string[]): string {
  return tags.join(', ')
}

export function TagInput({
  tags,
  onChange,
  placeholder = '输入后按 Enter 或逗号添加',
  label,
  description,
}: TagInputProps) {
  const [inputValue, setInputValue] = useState('')

  const addTags = (value: string) => {
    const newTags = parseCommaSeparated(value)
    if (newTags.length === 0) return

    const uniqueNewTags = newTags.filter(
      (tag) => !tags.some((t) => t.toLowerCase() === tag.toLowerCase())
    )
    if (uniqueNewTags.length > 0) {
      onChange([...tags, ...uniqueNewTags])
    }
    setInputValue('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addTags(inputValue)
    } else if (e.key === 'Backspace' && inputValue === '' && tags.length > 0) {
      // Remove last tag when backspace on empty input
      onChange(tags.slice(0, -1))
    }
  }

  const handleBlur = () => {
    if (inputValue.trim()) {
      addTags(inputValue)
    }
  }

  const removeTag = (index: number) => {
    onChange(tags.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-1.5">
      {label && (
        <label className="block text-sm font-medium text-neutral-300">{label}</label>
      )}
      {description && <p className="text-xs text-neutral-500 italic mb-2">{description}</p>}
      <div className="flex flex-wrap gap-2 p-2.5 glass-panel bg-neutral-900/40 rounded-xl min-h-[48px] focus-within:border-white/20 focus-within:bg-neutral-900/60 transition-all duration-300">
        {tags.map((tag, index) => (
          <span
            key={index}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-white/10 text-white text-xs font-medium rounded-lg border border-white/5 group/tag hover:bg-white/20 transition-colors"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(index)}
              className="text-neutral-500 hover:text-red-400 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </span>
        ))}
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          placeholder={tags.length === 0 ? placeholder : ''}
          className="flex-1 min-w-[140px] bg-transparent text-white text-sm outline-none placeholder:text-neutral-600 px-1"
        />
      </div>
      <p className="text-[10px] text-neutral-600 font-mono">
        TIP: SEPARATE WITH COMMAS OR PRESS ENTER (E.G. BTCUSDT, ETHUSDT)
      </p>
    </div>
  )
}
