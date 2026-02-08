import { useEffect, useState } from 'react';
import api from '../../../services/api';

interface DbStats {
  by_type?: Record<string, number>;
  earliest?: number;
  latest?: number;
  total?: number;
}

interface DbStatus {
  available: boolean;
  stats?: DbStats;
}

interface SignalItem {
  id: number | string;
  type: string;
  symbol: string;
  title: string;
  timestamp: number | string;
}

interface AlertsResponse {
  alerts?: SignalItem[];
  disabled?: boolean;
}

export const useDashboardData = () => {
  const [dbStatus, setDbStatus] = useState<DbStatus | null>(null);
  const [signals, setSignals] = useState<SignalItem[]>([]);
  const [alerts, setAlerts] = useState<SignalItem[]>([]);
  const [alertsDisabled, setAlertsDisabled] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    const results = await Promise.allSettled([
      api.get<DbStatus>('/db/status'),
      api.get<{ signals: SignalItem[] }>('/signals', { params: { limit: 5 } }),
      api.get<AlertsResponse>('/alerts', { params: { limit: 5 } }),
    ]);

    if (results[0].status === 'fulfilled') {
      setDbStatus(results[0].value.data ?? null);
    }
    if (results[1].status === 'fulfilled') {
      setSignals(results[1].value.data?.signals || []);
    }
    if (results[2].status === 'fulfilled') {
      const payload = results[2].value.data ?? {};
      if (payload.disabled) {
        setAlertsDisabled(true);
        setAlerts([]);
      } else {
        setAlertsDisabled(false);
        setAlerts(payload.alerts || []);
      }
    }
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  const byType = dbStatus?.stats?.by_type || {};
  const totalMessages = dbStatus?.stats?.total ?? 0;
  const signalCount = (byType['110'] || 0) + (byType['113'] || 0);
  const alertCount = alertsDisabled ? 0 : byType['112'] || 0;

  return {
    dbStatus,
    signals,
    alerts,
    alertsDisabled,
    loading,
    totalMessages,
    signalCount,
    alertCount,
    refresh: loadData,
  };
};
