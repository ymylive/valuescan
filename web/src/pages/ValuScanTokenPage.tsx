import React, { useState } from 'react';
import { GlassCard } from '../components/Common/GlassCard';
import { Key, Copy, Check, AlertCircle, RefreshCw } from 'lucide-react';
import api from '../services/api';

interface TokenStatus {
  valid: boolean | null;
  last_updated?: string;
  status_error?: string | null;
}

const ValuScanTokenPage: React.FC = () => {
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<TokenStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const consoleCommand =
    'JSON.stringify(Object.assign(Object.fromEntries(Object.keys(localStorage).map(k => [k, localStorage.getItem(k)])), Object.fromEntries(Object.keys(sessionStorage).map(k => [k, sessionStorage.getItem(k)]))), null, 2)';

  const statusLabel = status
    ? status.valid === true
      ? '有效'
      : status.valid === false
        ? '无效或已过期'
        : '状态未知'
    : '未检测';
  const statusDot = status
    ? status.valid === true
      ? 'bg-green-500'
      : status.valid === false
        ? 'bg-red-500'
        : 'bg-yellow-500'
    : 'bg-gray-400';

  const parseTokenInput = (raw: string) => {
    const text = raw.trim();
    if (!text) {
      throw new Error('请输入 Token JSON');
    }

    const stripWrappingQuotes = (value: string) => {
      if ((value.startsWith("'") && value.endsWith("'")) || (value.startsWith('"') && value.endsWith('"'))) {
        return value.slice(1, -1);
      }
      return value;
    };

    const tryParseJson = (value: string) => {
      try {
        return JSON.parse(value) as unknown;
      } catch {
        return null;
      }
    };

    const unescapeJsonLike = (value: string) => {
      return value
        .replace(/\\r\\n/g, '\n')
        .replace(/\\n/g, '\n')
        .replace(/\\t/g, '\t');
    };

    const decodeEscapedJson = (value: string) => {
      return value
        .replace(/\\r\\n/g, '\n')
        .replace(/\\n/g, '\n')
        .replace(/\\r/g, '\n')
        .replace(/\\t/g, '\t')
        .replace(/\\\\/g, '\\')
        .replace(/\\'/g, "'");
    };

    const parseObject = (value: string) => {
      let parsed = tryParseJson(value);
      if (typeof parsed === 'string') {
        parsed = tryParseJson(parsed);
      }
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>;
      }
      return null;
    };

    const parseFromBraceRange = (value: string) => {
      const start = value.indexOf('{');
      const end = value.lastIndexOf('}');
      if (start !== -1 && end !== -1 && end > start) {
        return parseObject(value.slice(start, end + 1));
      }
      return null;
    };

    const extractTokenFields = (value: string) => {
      const normalized = value.replace(/\\"/g, '"');
      const account =
        normalized.match(/"?account_token"?\s*:\s*"([^"]+)"/)?.[1] ??
        normalized.match(/"?account_token"?\s*:\s*'([^']+)'/)?.[1] ??
        normalized.match(/"?accessToken"?\s*:\s*"([^"]+)"/)?.[1] ??
        normalized.match(/"?accessToken"?\s*:\s*'([^']+)'/)?.[1];
      if (!account) {
        return null;
      }
      const refresh =
        normalized.match(/"?refresh_token"?\s*:\s*"([^"]+)"/)?.[1] ??
        normalized.match(/"?refresh_token"?\s*:\s*'([^']+)'/)?.[1] ??
        normalized.match(/"?refreshToken"?\s*:\s*"([^"]+)"/)?.[1] ??
        normalized.match(/"?refreshToken"?\s*:\s*'([^']+)'/)?.[1];
      const payload: Record<string, unknown> = { account_token: account };
      if (refresh) {
        payload.refresh_token = refresh;
      }
      return payload;
    };

    const parseQuotedJsonObject = (value: string) => {
      const trimmed = value.trim();
      const isSingleQuoted = trimmed.startsWith("'") && trimmed.endsWith("'");
      const isDoubleQuoted = trimmed.startsWith('"') && trimmed.endsWith('"');
      if (!isSingleQuoted && !isDoubleQuoted) {
        return null;
      }
      if (isDoubleQuoted) {
        const decoded = tryParseJson(trimmed);
        if (typeof decoded === 'string') {
          return parseObject(decoded) || parseFromBraceRange(decoded);
        }
        if (decoded && typeof decoded === 'object' && !Array.isArray(decoded)) {
          return decoded as Record<string, unknown>;
        }
        return null;
      }

      const inner = trimmed.slice(1, -1);
      const decoded = decodeEscapedJson(inner);
      return parseObject(decoded) || parseFromBraceRange(decoded);
    };

    const quotedParsed = parseQuotedJsonObject(text);
    if (quotedParsed) {
      return quotedParsed;
    }

    if (/\\[nrt"\\]/.test(text)) {
      const decoded = decodeEscapedJson(text);
      const parsed = parseObject(decoded) || parseFromBraceRange(decoded);
      if (parsed) {
        return parsed;
      }
    }

    const extracted =
      extractTokenFields(text) ||
      extractTokenFields(stripWrappingQuotes(text)) ||
      extractTokenFields(unescapeJsonLike(text)) ||
      extractTokenFields(decodeEscapedJson(text));
    if (extracted) {
      return extracted;
    }

    const candidates = [
      text,
      stripWrappingQuotes(text),
      unescapeJsonLike(stripWrappingQuotes(text)),
      unescapeJsonLike(text),
    ];

    for (const candidate of candidates) {
      const parsed = parseObject(candidate) || parseFromBraceRange(candidate);
      if (parsed) {
        return parsed;
      }
    }

    throw new Error('Token 格式无效，请粘贴 JSON.stringify 输出或完整 JSON');
  };

  const checkTokenStatus = async () => {
    setStatusLoading(true);
    try {
      const response = (await api.get('/valuescan/token/status')) as any;
      const valid = (response?.valid ?? response?.token_valid ?? null) as boolean | null;
      setStatus({
        valid,
        last_updated: response?.last_updated,
        status_error: response?.status_error ?? null,
      });
    } catch {
      setStatus({ valid: false });
    } finally {
      setStatusLoading(false);
    }
  };

  const handleCopyCommand = () => {
    navigator.clipboard.writeText(consoleCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSubmit = async () => {
    setLoading(true);
    setMessage(null);

    try {
      const tokenData = parseTokenInput(token);
      const response = (await api.post('/valuescan/token/update', { token: tokenData })) as any;

      if (response?.success) {
        setMessage({ type: 'success', text: response.message || 'Token 更新成功' });
        setToken('');
        checkTokenStatus();
      } else {
        setMessage({ type: 'error', text: response?.error || 'Token 更新失败' });
      }
    } catch (error: any) {
      const fallback = error instanceof Error ? error.message : 'Token 更新失败';
      setMessage({ type: 'error', text: error?.response?.data?.error || fallback });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <Key className="text-green-500" size={28} />
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">ValuScan Token 管理</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              手动更新 Token，立即刷新服务认证状态
            </p>
          </div>
        </div>
        <button
          onClick={checkTokenStatus}
          disabled={statusLoading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white text-sm font-medium transition-colors"
        >
          <RefreshCw size={18} className={statusLoading ? 'animate-spin' : ''} />
          {statusLoading ? '检测中...' : '刷新状态'}
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <GlassCard className="p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">获取 Token 步骤</h2>
          <div className="space-y-4">
            <div className="flex gap-3">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-green-500 text-white flex items-center justify-center text-sm font-bold">1</div>
              <div>
                <p className="text-gray-700 dark:text-gray-300">
                  打开 <a href="https://www.valuescan.io" target="_blank" rel="noopener noreferrer" className="text-green-500 hover:underline">ValuScan 官网</a> 并登录账号
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-green-500 text-white flex items-center justify-center text-sm font-bold">2</div>
              <div>
                <p className="text-gray-700 dark:text-gray-300">
                  按 <code className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-sm">F12</code> 打开开发者工具，切换到 <code className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-sm">Console</code> 标签
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-green-500 text-white flex items-center justify-center text-sm font-bold">3</div>
              <div className="w-full">
                <p className="text-gray-700 dark:text-gray-300 mb-2">在控制台粘贴以下命令获取所有存储数据</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 px-3 py-2 bg-gray-900 dark:bg-gray-800 text-green-400 rounded text-sm font-mono overflow-x-auto">
                    {consoleCommand}
                  </code>
                  <button
                    onClick={handleCopyCommand}
                    className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                    title="复制命令"
                  >
                    {copied ? <Check size={18} className="text-green-500" /> : <Copy size={18} className="text-gray-500" />}
                  </button>
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-green-500 text-white flex items-center justify-center text-sm font-bold">4</div>
              <div>
                <p className="text-gray-700 dark:text-gray-300">
                  复制完整输出的 JSON 字符串，粘贴到下方输入框（包含 accessToken / refreshToken 等字段）
                </p>
              </div>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Token 状态</h2>
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${statusDot}`} />
            <span className="text-gray-700 dark:text-gray-300">{statusLabel}</span>
          </div>
          {!status && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              点击刷新状态获取最新结果
            </p>
          )}
          {status?.last_updated && (
            <p className="text-sm text-gray-500 mt-2">
              最近更新: {new Date(status.last_updated).toLocaleString()}
            </p>
          )}
          {status?.status_error && (
            <p className="text-xs text-amber-500 mt-1">
              检测异常: {status.status_error}
            </p>
          )}
        </GlassCard>
      </div>

      <GlassCard className="p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">输入 Token</h2>
        <textarea
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder='{"accessToken":"...","refreshToken":"...","expiresIn":...}'
          className="w-full h-32 px-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 font-mono text-sm resize-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
        />

        {message && (
          <div className={`flex items-center gap-2 mt-3 p-3 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
              : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
          }`}>
            {message.type === 'success' ? <Check size={18} /> : <AlertCircle size={18} />}
            <span>{message.text}</span>
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={loading || !token.trim()}
          className="mt-4 w-full py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <RefreshCw size={18} className="animate-spin" />
              更新中...
            </>
          ) : (
            <>
              <Key size={18} />
              更新 Token
            </>
          )}
        </button>
      </GlassCard>

      <div className="text-sm text-gray-500 dark:text-gray-400 space-y-1">
        <p>* Token 有效期通常为 7 天，请定期手动更新</p>
        <p>* 请确保 ValuScan 账号已登录并处于可用状态</p>
        <p>* Token 包含敏感信息，请勿随意分享</p>
      </div>
    </div>
  );
};

export default ValuScanTokenPage;
