import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { Save, RefreshCw, FileJson, Copy } from 'lucide-react'
import { api } from '../../lib/api'

type ArtifactName = 'cookies' | 'localstorage' | 'sessionstorage'

function safeJsonParse(
  text: string
): { ok: true; value: any } | { ok: false; error: string } {
  const trimmed = (text || '').trim()
  if (!trimmed) return { ok: true, value: null }
  try {
    return { ok: true, value: JSON.parse(trimmed) }
  } catch (e: any) {
    return { ok: false, error: e?.message || 'JSON 解析失败' }
  }
}

function formatJson(text: string): string {
  const parsed = safeJsonParse(text)
  if (!parsed.ok) return text
  if (parsed.value === null) return ''
  try {
    return JSON.stringify(parsed.value, null, 2)
  } catch {
    return text
  }
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).then(
    () => toast.success('已复制到剪贴板'),
    () => toast.error('复制失败')
  )
}

export function ValueScanDataEditor() {
  const [loading, setLoading] = useState(true)
  const [savingArtifacts, setSavingArtifacts] = useState(false)
  const [savingCoinpool, setSavingCoinpool] = useState(false)

  const [paths, setPaths] = useState<{
    cookies_file: string
    localstorage_file: string
    sessionstorage_file: string
  } | null>(null)
  const [artifactText, setArtifactText] = useState<
    Record<ArtifactName, string>
  >({
    cookies: '',
    localstorage: '',
    sessionstorage: '',
  })

  const [coinpool, setCoinpool] = useState<any>(null)
  const [coinpoolPath, setCoinpoolPath] = useState<string>('')

  const coinpoolApiUrl = useMemo(() => {
    if (!coinpool) return ''
    const host = String(coinpool.host || '127.0.0.1').trim()
    const port = String(coinpool.port || 30006).trim()
    return `http://${host}:${port}/api/ai500/list`
  }, [coinpool])

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [artifacts, coinpoolCfg] = await Promise.all([
        api.getValuescanArtifacts(),
        api.getValuescanCoinPoolConfig(),
      ])
      setPaths(artifacts.paths)
      setArtifactText({
        cookies: JSON.stringify(artifacts.cookies ?? [], null, 2),
        localstorage: JSON.stringify(artifacts.localstorage ?? {}, null, 2),
        sessionstorage: JSON.stringify(artifacts.sessionstorage ?? {}, null, 2),
      })
      setCoinpool(coinpoolCfg.config)
      setCoinpoolPath(coinpoolCfg.path)
    } catch (e: any) {
      toast.error(e?.message || '加载 ValueScan 数据失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search)
      if (params.get('valuescan_login') === '1') {
        toast.success('已从浏览器导入 ValueScan 登录信息')
        loadAll()
      }
    } catch {
      /* ignore */
    }
  }, [loadAll])

  const handleSaveArtifacts = async () => {
    const parsedCookies = safeJsonParse(artifactText.cookies)
    const parsedLocal = safeJsonParse(artifactText.localstorage)
    const parsedSession = safeJsonParse(artifactText.sessionstorage)

    const errors: string[] = []
    if (!parsedCookies.ok) errors.push(`cookies: ${parsedCookies.error}`)
    if (!parsedLocal.ok) errors.push(`localStorage: ${parsedLocal.error}`)
    if (!parsedSession.ok) errors.push(`sessionStorage: ${parsedSession.error}`)
    if (errors.length) {
      toast.error('请先修复 JSON 格式', { description: errors.join('\n') })
      return
    }

    setSavingArtifacts(true)
    try {
      const result = await api.saveValuescanArtifacts({
        cookies: parsedCookies.ok ? parsedCookies.value : undefined,
        localstorage: parsedLocal.ok ? parsedLocal.value : undefined,
        sessionstorage: parsedSession.ok ? parsedSession.value : undefined,
      })
      if (result.success) toast.success('已保存 ValueScan 登录数据')
      else toast.error((result.errors || []).join(', ') || '保存失败')
    } catch (e: any) {
      toast.error(e?.message || '保存失败')
    } finally {
      setSavingArtifacts(false)
    }
  }

  const handleSaveCoinpool = async () => {
    setSavingCoinpool(true)
    try {
      const result = await api.saveValuescanCoinPoolConfig(coinpool)
      if (result.success) {
        toast.success('已保存 AI 选币数据源配置')
        setCoinpool(result.config || coinpool)
      } else {
        toast.error(
          result.error || (result.errors || []).join(', ') || '保存失败'
        )
      }
    } catch (e: any) {
      toast.error(e?.message || '保存失败')
    } finally {
      setSavingCoinpool(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-[#F0B90B]" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="bg-[#1E2329] border border-[#2B3139] rounded-xl p-4 sm:p-6 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-white">
              ValueScan 登录数据
            </h3>
            <div className="text-xs text-gray-400">
              直接编辑本地文件（cookies / localStorage /
              sessionStorage），用于轮询/自动登录/抓取等模块
            </div>
            {paths && (
              <div className="text-xs text-gray-500 mt-2 space-y-1">
                <div>cookies: {paths.cookies_file}</div>
                <div>localStorage: {paths.localstorage_file}</div>
                <div>sessionStorage: {paths.sessionstorage_file}</div>
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={loadAll}
              className="flex items-center gap-2 px-3 py-2 bg-[#2B3139] hover:bg-[#3B4149] rounded-lg text-white text-sm"
            >
              <RefreshCw className="w-4 h-4" />
              刷新
            </button>
            <button
              onClick={handleSaveArtifacts}
              disabled={savingArtifacts}
              className="flex items-center gap-2 px-3 py-2 bg-[#F0B90B] hover:bg-[#d4a50a] disabled:bg-gray-600 rounded-lg text-black text-sm font-medium"
            >
              <Save className="w-4 h-4" />
              {savingArtifacts ? '保存中…' : '保存'}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {(
            ['cookies', 'localstorage', 'sessionstorage'] as ArtifactName[]
          ).map((name) => (
            <div
              key={name}
              className="bg-[#0B0E11] border border-[#2B3139] rounded-xl p-3 space-y-2"
            >
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-200 flex items-center gap-2">
                  <FileJson className="w-4 h-4 text-[#F0B90B]" />
                  {name === 'cookies'
                    ? 'cookies'
                    : name === 'localstorage'
                      ? 'localStorage'
                      : 'sessionStorage'}
                </div>
                <button
                  onClick={() =>
                    setArtifactText((prev) => ({
                      ...prev,
                      [name]: formatJson(prev[name]),
                    }))
                  }
                  className="text-xs text-gray-400 hover:text-white"
                >
                  格式化
                </button>
              </div>
              <textarea
                value={artifactText[name]}
                onChange={(e) =>
                  setArtifactText((prev) => ({
                    ...prev,
                    [name]: e.target.value,
                  }))
                }
                rows={12}
                className="w-full px-3 py-2 bg-[#0B0E11] border border-[#2B3139] rounded-lg text-xs text-gray-200 font-mono focus:outline-none focus:border-[#F0B90B]"
                placeholder="粘贴 JSON…（留空表示不改；保存时会写入文件）"
              />
            </div>
          ))}
        </div>
      </div>

      <div className="bg-[#1E2329] border border-[#2B3139] rounded-xl p-4 sm:p-6 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-white">
              AI 智能选币数据源（本地 AI500 API）
            </h3>
            <div className="text-xs text-gray-400">
              用于把 ValueScan 页面表格输出为交易系统可消费的候选币列表
            </div>
            {coinpoolPath && (
              <div className="text-xs text-gray-500 mt-2">
                配置文件：{coinpoolPath}
              </div>
            )}
          </div>
          <button
            onClick={handleSaveCoinpool}
            disabled={savingCoinpool || !coinpool}
            className="flex items-center gap-2 px-3 py-2 bg-[#F0B90B] hover:bg-[#d4a50a] disabled:bg-gray-600 rounded-lg text-black text-sm font-medium"
          >
            <Save className="w-4 h-4" />
            {savingCoinpool ? '保存中…' : '保存'}
          </button>
        </div>

        {coinpool && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    host
                  </label>
                  <input
                    value={coinpool.host ?? ''}
                    onChange={(e) =>
                      setCoinpool((p: any) => ({ ...p, host: e.target.value }))
                    }
                    className="w-full px-3 py-2 bg-[#0B0E11] border border-[#2B3139] rounded-lg text-white focus:outline-none focus:border-[#F0B90B]"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    port
                  </label>
                  <input
                    type="number"
                    value={coinpool.port ?? 30006}
                    onChange={(e) =>
                      setCoinpool((p: any) => ({
                        ...p,
                        port: Number(e.target.value),
                      }))
                    }
                    className="w-full px-3 py-2 bg-[#0B0E11] border border-[#2B3139] rounded-lg text-white focus:outline-none focus:border-[#F0B90B]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  tab（机会监控/风险监控/手动监控）
                </label>
                <input
                  value={coinpool.tab ?? ''}
                  onChange={(e) =>
                    setCoinpool((p: any) => ({ ...p, tab: e.target.value }))
                  }
                  className="w-full px-3 py-2 bg-[#0B0E11] border border-[#2B3139] rounded-lg text-white focus:outline-none focus:border-[#F0B90B]"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">url</label>
                <input
                  value={coinpool.url ?? ''}
                  onChange={(e) =>
                    setCoinpool((p: any) => ({ ...p, url: e.target.value }))
                  }
                  className="w-full px-3 py-2 bg-[#0B0E11] border border-[#2B3139] rounded-lg text-white focus:outline-none focus:border-[#F0B90B]"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <label className="inline-flex items-center gap-2 select-none text-sm text-gray-300">
                  <input
                    type="checkbox"
                    checked={Boolean(coinpool.headless)}
                    onChange={(e) =>
                      setCoinpool((p: any) => ({
                        ...p,
                        headless: e.target.checked,
                      }))
                    }
                    className="w-4 h-4 text-[#F0B90B] bg-[#0B0E11] border-[#2B3139] rounded focus:ring-[#F0B90B]"
                  />
                  headless
                </label>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    chrome_debug_port
                  </label>
                  <input
                    type="number"
                    value={coinpool.chrome_debug_port ?? 9222}
                    onChange={(e) =>
                      setCoinpool((p: any) => ({
                        ...p,
                        chrome_debug_port: Number(e.target.value),
                      }))
                    }
                    className="w-full px-3 py-2 bg-[#0B0E11] border border-[#2B3139] rounded-lg text-white focus:outline-none focus:border-[#F0B90B]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  user_data_path
                </label>
                <input
                  value={coinpool.user_data_path ?? ''}
                  onChange={(e) =>
                    setCoinpool((p: any) => ({
                      ...p,
                      user_data_path: e.target.value,
                    }))
                  }
                  className="w-full px-3 py-2 bg-[#0B0E11] border border-[#2B3139] rounded-lg text-white focus:outline-none focus:border-[#F0B90B]"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    max_pages
                  </label>
                  <input
                    type="number"
                    value={coinpool.max_pages ?? 1}
                    onChange={(e) =>
                      setCoinpool((p: any) => ({
                        ...p,
                        max_pages: Number(e.target.value),
                      }))
                    }
                    className="w-full px-3 py-2 bg-[#0B0E11] border border-[#2B3139] rounded-lg text-white focus:outline-none focus:border-[#F0B90B]"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    limit
                  </label>
                  <input
                    type="number"
                    value={coinpool.limit ?? 200}
                    onChange={(e) =>
                      setCoinpool((p: any) => ({
                        ...p,
                        limit: Number(e.target.value),
                      }))
                    }
                    className="w-full px-3 py-2 bg-[#0B0E11] border border-[#2B3139] rounded-lg text-white focus:outline-none focus:border-[#F0B90B]"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    cache_ttl_s
                  </label>
                  <input
                    type="number"
                    value={coinpool.cache_ttl_s ?? 15}
                    onChange={(e) =>
                      setCoinpool((p: any) => ({
                        ...p,
                        cache_ttl_s: Number(e.target.value),
                      }))
                    }
                    className="w-full px-3 py-2 bg-[#0B0E11] border border-[#2B3139] rounded-lg text-white focus:outline-none focus:border-[#F0B90B]"
                  />
                </div>
              </div>
            </div>

            <div className="bg-[#0B0E11] border border-[#2B3139] rounded-xl p-4 space-y-3">
              <div className="text-sm text-gray-200">交易系统接入</div>
              <div className="text-xs text-gray-400">
                把下面 URL 配置为 AI500 / coinpool 数据源：
              </div>
              <div className="flex items-center gap-2">
                <code className="flex-1 px-3 py-2 bg-black/30 border border-[#2B3139] rounded-lg text-xs text-gray-200 overflow-auto">
                  {coinpoolApiUrl}
                </code>
                <button
                  onClick={() => copyToClipboard(coinpoolApiUrl)}
                  className="p-2 bg-[#2B3139] hover:bg-[#3B4149] rounded-lg text-white"
                  aria-label="复制"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>

              <div className="text-xs text-gray-400 mt-3">
                启动抓取服务（会读取上面的配置文件）：
              </div>
              <div className="flex items-center gap-2">
                <code className="flex-1 px-3 py-2 bg-black/30 border border-[#2B3139] rounded-lg text-xs text-gray-200 overflow-auto">
                  python -m signal_monitor.ai_coin_pool_server
                </code>
                <button
                  onClick={() =>
                    copyToClipboard(
                      'python -m signal_monitor.ai_coin_pool_server'
                    )
                  }
                  className="p-2 bg-[#2B3139] hover:bg-[#3B4149] rounded-lg text-white"
                  aria-label="复制"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>
              <div className="text-xs text-gray-500">
                提示：首次需要先用有头模式登录一次（`signal_monitor/start_with_chrome.py`），之后可用
                headless 长期运行
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
