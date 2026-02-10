import { useState, useRef, useEffect } from 'react';
import { Upload, Download, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '../ui/Button';
import { GlassCard } from '../shared/GlassCard';

interface TokenStatus {
  exists: boolean;
  valid?: boolean;
  hasToken?: boolean;
  modified_time?: string;
  size?: number;
  cookiesExists?: boolean;
  cookiesModifiedTime?: string;
  cookiesSize?: number;
  hasCookies?: boolean;
}

export const TokenUpload = () => {
  const [status, setStatus] = useState<TokenStatus | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const apiBase = typeof window !== 'undefined' ? window.location.origin : '';

  const checkStatus = async () => {
    try {
      const res = await fetch('/api/token/status');
      const data = await res.json();
      setStatus(data);
    } catch {
      setStatus(null);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setMessage('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/token/upload', { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok) {
        const label = data?.kind === 'cookies' ? 'Cookie' : 'Token';
        setMessage(`${label} 上传成功`);
        checkStatus();
      } else {
        setMessage(data.error || data.message || '上传失败');
      }
    } catch {
      setMessage('上传失败');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDownload = (kind: 'token' | 'cookies') => {
    const query = kind === 'cookies' ? '?kind=cookies' : '';
    window.open(`/api/token/download${query}`, '_blank');
  };

  useEffect(() => { checkStatus(); }, []);

  const cookieUploadCommand = `fetch('${apiBase}/api/token/upload', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cookies:document.cookie.split(';').map(item=>{const parts=item.split('=');return {name:parts.shift()?.trim()||'',value:parts.join('=').trim(),domain:location.hostname,path:'/'};}).filter(c=>c.name)})})}).then(r=>r.json()).then(console.log).catch(console.error);`;
  const cookieExportCommand = "Object.assign(document.createElement('a'),{href:'data:application/json,'+encodeURIComponent(JSON.stringify(document.cookie.split(';').map(item=>{const parts=item.split('=');return {name:parts.shift()?.trim()||'',value:parts.join('=').trim(),domain:location.hostname,path:'/'};}).filter(c=>c.name),null,2)),download:'valuescan_cookies.json'}).click()";

  return (
    <GlassCard className="p-4">
      <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">ValueScan 认证</h3>
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          {status?.hasCookies ? (
            <><CheckCircle className="text-green-500" size={20} /><span className="text-green-600 dark:text-green-400">Cookie 已配置</span></>
          ) : (
            <><AlertCircle className="text-yellow-500" size={20} /><span className="text-yellow-600 dark:text-yellow-400">未配置 Cookie</span></>
          )}
        </div>
        {status?.cookiesModifiedTime && <p className="text-sm text-gray-500">Cookie 更新时间: {status.cookiesModifiedTime}</p>}
        {status?.hasToken && <p className="text-xs text-gray-500">Token(localStorage) 已配置</p>}
        {status?.modified_time && <p className="text-xs text-gray-500">Token 更新时间: {status.modified_time}</p>}
        <div className="flex gap-3">
          <input ref={fileInputRef} type="file" accept=".json" onChange={handleUpload} className="hidden" />
          <Button variant="secondary" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            <Upload className="w-4 h-4 mr-2" />{uploading ? '上传中...' : '上传 Cookie'}
          </Button>
          {status?.cookiesExists && (
            <Button variant="secondary" onClick={() => handleDownload('cookies')}>
              <Download className="w-4 h-4 mr-2" />下载 Cookie
            </Button>
          )}
          {status?.exists && (
            <Button variant="secondary" onClick={() => handleDownload('token')}>
              <Download className="w-4 h-4 mr-2" />下载 Token
            </Button>
          )}
        </div>
        {message && <p className={`text-sm ${message.includes('成功') ? 'text-green-600' : 'text-red-600'}`}>{message}</p>}
        <div className="text-xs text-gray-500 space-y-1">
          <p>自动上传 Cookie: 在 valuescan.io 登录后按 F12，在控制台执行:</p>
          <code className="block bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs break-all select-all">
            {cookieUploadCommand}
          </code>
          <p>仅导出 Cookie 文件:</p>
          <code className="block bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs break-all select-all">
            {cookieExportCommand}
          </code>
        </div>
      </div>
    </GlassCard>
  );
};
