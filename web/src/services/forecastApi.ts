import api from './api';

export type ForecastResponse = {
  success: boolean;
  data?: Record<string, unknown>;
  error?: string;
};

export const fetchForecast = async (symbol: string, useLlm: boolean): Promise<ForecastResponse> => {
  const encoded = encodeURIComponent(symbol);
  return api.get(`/v1/market/forecast/${encoded}`, {
    params: { use_llm: useLlm ? 1 : 0 },
    timeout: 300000,
  });
};
