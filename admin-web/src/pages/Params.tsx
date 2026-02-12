import { useState, useEffect } from 'react'
import { api } from '../services/api'
import { useTheme } from '../hooks/useTheme'

export const Params = () => {
  const { theme } = useTheme()
  const [config, setConfig] = useState<Record<string, any>>({})
  const [jsonMode, setJsonMode] = useState(false)
  const [jsonText, setJsonText] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)

  const isDark = theme === 'day'
  const border = isDark ? 'border-white/20' : 'border-black/20'
  const hover = isDark ? 'hover:bg-white/10' : 'hover:bg-black/10'
  const bg = isDark ? 'bg-black' : 'bg-white'
  const text = isDark ? 'text-white' : 'text-black'

  useEffect(() => {
    api.config.get().then(data => {
      setConfig(data)
      setJsonText(JSON.stringify(data, null, 2))
      setLoading(false)
    }).catch(e => {
      setStatus(`Error: ${e.message}`)
      setLoading(false)
    })
  }, [])

  const save = async () => {
    setStatus('Saving...')
    try {
      const data = jsonMode ? JSON.parse(jsonText) : config
      await api.config.update(data)
      setStatus('Saved successfully. Restart may be required.')
    } catch (e) {
      setStatus(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  if (loading) return <div>Loading...</div>

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl">Configuration</h2>
        <button
          onClick={() => setJsonMode(!jsonMode)}
          className={`border ${border} ${hover} px-4 py-2 transition-colors`}
        >
          {jsonMode ? 'Form View' : 'JSON View'}
        </button>
      </div>

      {jsonMode ? (
        <textarea
          value={jsonText}
          onChange={e => setJsonText(e.target.value)}
          className={`w-full h-96 ${bg} ${text} border ${border} p-4 font-mono`}
        />
      ) : (
        <div className={`border ${border} p-6 space-y-4`}>
          {Object.entries(config).map(([key, value]) => (
            <div key={key}>
              <label className="block text-sm opacity-60 mb-1">{key}</label>
              <input
                type="text"
                value={typeof value === 'object' ? JSON.stringify(value) : value}
                onChange={e => setConfig({ ...config, [key]: e.target.value })}
                className={`w-full ${bg} ${text} border ${border} px-3 py-2`}
              />
            </div>
          ))}
        </div>
      )}

      <button
        onClick={save}
        className={`border ${border} ${hover} px-6 py-3 transition-colors`}
      >
        Save Configuration
      </button>

      {status && (
        <div className={`border ${border} p-4`}>
          {status}
        </div>
      )}
    </div>
  )
}
