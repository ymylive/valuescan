import { useEffect, useMemo, useRef, useState } from 'react'
import { Eye, EyeOff, Search } from 'lucide-react'

type ConfigPrimitive = string | number | boolean | null
type ConfigValue =
  | ConfigPrimitive
  | ConfigValue[]
  | { [key: string]: ConfigValue }

function isSensitiveKey(key: string): boolean {
  return /(secret|password|token|api[_-]?key|api[_-]?secret|api[_-]?hash|private)/i.test(
    key
  )
}

function getValueKind(
  value: unknown
): 'null' | 'array' | 'object' | 'string' | 'number' | 'boolean' | 'unknown' {
  if (value === null) return 'null'
  if (Array.isArray(value)) return 'array'
  switch (typeof value) {
    case 'string':
      return 'string'
    case 'number':
      return 'number'
    case 'boolean':
      return 'boolean'
    case 'object':
      return 'object'
    default:
      return 'unknown'
  }
}

function tryJsonStringify(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2) ?? ''
  } catch {
    return String(value)
  }
}

function FieldRow({
  sectionKey,
  fieldKey,
  value,
  onChange,
  setFieldError,
}: {
  sectionKey: string
  fieldKey: string
  value: ConfigValue
  onChange: (key: string, value: ConfigValue) => void
  setFieldError: (fieldId: string, error: string | null) => void
}) {
  const fieldId = `${sectionKey}.${fieldKey}`
  const kind = getValueKind(value)

  if (kind === 'boolean') {
    return (
      <div className="py-3 sm:py-4 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
        <div className="sm:w-72">
          <label className="block text-sm text-gray-300 break-all">
            {fieldKey.toUpperCase()}
          </label>
          <div className="text-xs text-gray-500">boolean</div>
        </div>
        <div className="flex-1">
          <label className="inline-flex items-center gap-2 select-none">
            <input
              type="checkbox"
              checked={Boolean(value)}
              onChange={(e) => onChange(fieldKey, e.target.checked)}
              className="w-4 h-4 text-[#F0B90B] bg-[#0B0E11] border-[#2B3139] rounded focus:ring-[#F0B90B]"
            />
            <span className="text-sm text-gray-300">
              {value ? '启用' : '禁用'}
            </span>
          </label>
        </div>
      </div>
    )
  }

  if (kind === 'number') {
    return (
      <NumberFieldRow
        fieldId={fieldId}
        fieldKey={fieldKey}
        value={value}
        onChange={onChange}
        setFieldError={setFieldError}
      />
    )
  }

  if (kind === 'string') {
    return (
      <StringFieldRow fieldKey={fieldKey} value={value} onChange={onChange} />
    )
  }

  if (kind === 'null') {
    return (
      <NullFieldRow
        fieldId={fieldId}
        fieldKey={fieldKey}
        value={value}
        onChange={onChange}
        setFieldError={setFieldError}
      />
    )
  }

  return (
    <JsonFieldRow
      fieldId={fieldId}
      fieldKey={fieldKey}
      kind={kind}
      value={value}
      onChange={onChange}
      setFieldError={setFieldError}
    />
  )
}

function NumberFieldRow({
  fieldId,
  fieldKey,
  value,
  onChange,
  setFieldError,
}: {
  fieldId: string
  fieldKey: string
  value: ConfigValue
  onChange: (key: string, value: ConfigValue) => void
  setFieldError: (fieldId: string, error: string | null) => void
}) {
  const [text, setText] = useState(String(value))

  useEffect(() => {
    setText(String(value))
  }, [value])

  const handleChange = (next: string) => {
    setText(next)
    if (next.trim() === '') {
      setFieldError(fieldId, '不能为空')
      return
    }
    const num = Number(next)
    if (!Number.isFinite(num)) {
      setFieldError(fieldId, '数字格式不正确')
      return
    }
    setFieldError(fieldId, null)
    onChange(fieldKey, num)
  }

  return (
    <div className="py-3 sm:py-4 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
      <div className="sm:w-72">
        <label className="block text-sm text-gray-300 break-all">
          {fieldKey.toUpperCase()}
        </label>
        <div className="text-xs text-gray-500">number</div>
      </div>
      <div className="flex-1">
        <input
          type="number"
          inputMode="decimal"
          step="any"
          value={text}
          onChange={(e) => handleChange(e.target.value)}
          className="w-full px-4 py-2 bg-[#0B0E11] border border-[#2B3139] rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-[#F0B90B]"
        />
      </div>
    </div>
  )
}

function StringFieldRow({
  fieldKey,
  value,
  onChange,
}: {
  fieldKey: string
  value: ConfigValue
  onChange: (key: string, value: ConfigValue) => void
}) {
  const sensitive = isSensitiveKey(fieldKey)
  const [show, setShow] = useState(false)

  return (
    <div className="py-3 sm:py-4 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
      <div className="sm:w-72">
        <label className="block text-sm text-gray-300 break-all">
          {fieldKey.toUpperCase()}
        </label>
        <div className="text-xs text-gray-500">string</div>
      </div>
      <div className="flex-1">
        <div className="relative">
          <input
            type={sensitive && !show ? 'password' : 'text'}
            value={String(value)}
            onChange={(e) => onChange(fieldKey, e.target.value)}
            className={`w-full px-4 py-2 bg-[#0B0E11] border border-[#2B3139] rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-[#F0B90B] ${sensitive ? 'pr-11' : ''}`}
          />
          {sensitive && (
            <button
              type="button"
              onClick={() => setShow((v) => !v)}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-gray-400 hover:text-white"
              aria-label={show ? '隐藏' : '显示'}
            >
              {show ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function NullFieldRow({
  fieldId,
  fieldKey,
  value,
  onChange,
  setFieldError,
}: {
  fieldId: string
  fieldKey: string
  value: ConfigValue
  onChange: (key: string, value: ConfigValue) => void
  setFieldError: (fieldId: string, error: string | null) => void
}) {
  const [mode, setMode] = useState<'none' | 'text'>('none')
  const [text, setText] = useState('')

  useEffect(() => {
    setMode(value === null ? 'none' : 'text')
    setText(value === null ? '' : String(value))
  }, [value])

  return (
    <div className="py-3 sm:py-4 flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-4">
      <div className="sm:w-72">
        <label className="block text-sm text-gray-300 break-all">
          {fieldKey.toUpperCase()}
        </label>
        <div className="text-xs text-gray-500">null / string</div>
      </div>
      <div className="flex-1 space-y-2">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => {
              setMode('none')
              setFieldError(fieldId, null)
              onChange(fieldKey, null)
            }}
            className={`px-3 py-2 rounded-lg text-sm border ${
              mode === 'none'
                ? 'bg-[#F0B90B] border-[#F0B90B] text-black'
                : 'bg-[#0B0E11] border-[#2B3139] text-gray-300 hover:bg-[#12161c]'
            }`}
          >
            None
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('text')
              setFieldError(fieldId, null)
              onChange(fieldKey, text)
            }}
            className={`px-3 py-2 rounded-lg text-sm border ${
              mode === 'text'
                ? 'bg-[#F0B90B] border-[#F0B90B] text-black'
                : 'bg-[#0B0E11] border-[#2B3139] text-gray-300 hover:bg-[#12161c]'
            }`}
          >
            文本
          </button>
        </div>
        {mode === 'text' && (
          <input
            type="text"
            value={text}
            onChange={(e) => {
              setText(e.target.value)
              onChange(fieldKey, e.target.value)
            }}
            className="w-full px-4 py-2 bg-[#0B0E11] border border-[#2B3139] rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-[#F0B90B]"
          />
        )}
      </div>
    </div>
  )
}

function JsonFieldRow({
  fieldId,
  fieldKey,
  kind,
  value,
  onChange,
  setFieldError,
}: {
  fieldId: string
  fieldKey: string
  kind: ReturnType<typeof getValueKind>
  value: ConfigValue
  onChange: (key: string, value: ConfigValue) => void
  setFieldError: (fieldId: string, error: string | null) => void
}) {
  const pretty = useMemo(() => tryJsonStringify(value), [value])
  const lastPrettyRef = useRef(pretty)

  const [jsonText, setJsonText] = useState(pretty)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setJsonText((prev) => (prev === lastPrettyRef.current ? pretty : prev))
    lastPrettyRef.current = pretty
  }, [pretty])

  const handleJsonChange = (next: string) => {
    setJsonText(next)
    try {
      const parsed = JSON.parse(next) as ConfigValue
      setError(null)
      setFieldError(fieldId, null)
      onChange(fieldKey, parsed)
    } catch {
      const msg = 'JSON 格式不正确'
      setError(msg)
      setFieldError(fieldId, msg)
    }
  }

  return (
    <div className="py-3 sm:py-4 flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-4">
      <div className="sm:w-72">
        <label className="block text-sm text-gray-300 break-all">
          {fieldKey.toUpperCase()}
        </label>
        <div className="text-xs text-gray-500">{kind}</div>
      </div>
      <div className="flex-1 space-y-2">
        <textarea
          value={jsonText}
          onChange={(e) => handleJsonChange(e.target.value)}
          rows={6}
          className="w-full px-4 py-2 bg-[#0B0E11] border border-[#2B3139] rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-[#F0B90B] font-mono text-xs sm:text-sm"
        />
        {error && <div className="text-xs text-red-400">{error}</div>}
        {!error && (
          <div className="text-xs text-gray-500">使用 JSON 编辑数组/对象</div>
        )}
      </div>
    </div>
  )
}

export function ConfigSectionEditor({
  title,
  icon,
  sectionKey,
  data,
  onChangeField,
  setFieldError,
}: {
  title: string
  icon?: React.ReactNode
  sectionKey: string
  data: Record<string, ConfigValue>
  onChangeField: (key: string, value: ConfigValue) => void
  setFieldError: (fieldId: string, error: string | null) => void
}) {
  const [query, setQuery] = useState('')

  const keys = useMemo(() => {
    const all = Object.keys(data || {})
    all.sort((a, b) => a.localeCompare(b))
    if (!query.trim()) return all
    const q = query.trim().toLowerCase()
    return all.filter((k) => k.toLowerCase().includes(q))
  }, [data, query])

  return (
    <div className="bg-[#1E2329] border border-[#2B3139] rounded-xl p-4 sm:p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          {icon}
          <h3 className="text-lg font-semibold text-white">{title}</h3>
        </div>
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索参数名..."
            className="w-full pl-10 pr-3 py-2 bg-[#0B0E11] border border-[#2B3139] rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-[#F0B90B] text-sm"
          />
        </div>
      </div>

      <div className="divide-y divide-[#2B3139]">
        {keys.length === 0 ? (
          <div className="py-10 text-center text-gray-400 text-sm">
            没有匹配的参数
          </div>
        ) : (
          keys.map((k) => (
            <FieldRow
              key={k}
              sectionKey={sectionKey}
              fieldKey={k}
              value={data[k]}
              onChange={onChangeField}
              setFieldError={setFieldError}
            />
          ))
        )}
      </div>
    </div>
  )
}
