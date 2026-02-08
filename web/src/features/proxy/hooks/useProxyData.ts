import { useState, useEffect, useCallback } from 'react';

interface ClashServiceStatus {
  running: boolean;
  port: number;
  api_url: string;
  error?: string;
}

export const useProxyData = () => {
  const [serviceStatus, setServiceStatus] = useState<ClashServiceStatus | null>(null);
  const [checking, setChecking] = useState(true);
  const [loading, setLoading] = useState(false);

  const checkStatus = useCallback(async () => {
    setChecking(true);
    try {
      const res = await fetch('/api/clash/service/status');
      setServiceStatus(await res.json());
    } catch {
      setServiceStatus({ running: false, port: 9090, api_url: 'http://127.0.0.1:9090', error: '无法连接' });
    } finally {
      setChecking(false);
    }
  }, []);

  const startService = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/clash/service/start', { method: 'POST' });
      if (res.ok) await checkStatus();
    } finally {
      setLoading(false);
    }
  };

  const updateSubscription = async (url: string, type: 'clash' | 'base64') => {
    try {
      const res = await fetch('/api/clash/subscription/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, type }),
      });
      const data = await res.json();
      if (res.ok) return { success: true, count: data.count };
      return { success: false, error: data.error };
    } catch {
      return { success: false, error: '请求失败' };
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 10000);
    return () => clearInterval(interval);
  }, [checkStatus]);

  return { serviceStatus, checking, loading, checkStatus, startService, updateSubscription };
};
