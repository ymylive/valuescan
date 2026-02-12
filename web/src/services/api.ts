import axios from 'axios';

export type ApiError = {
  message: string;
  status?: number;
  data?: unknown;
};

const ADMIN_TOKEN_KEY = 'token';
const API_HOST_MAPPING: Record<string, string> = {
  'testvalue.cornna.xyz': 'https://api.testvalue.cornna.xyz/api',
};

const resolveApiBaseUrl = (): string => {
  const envBase = ((import.meta as unknown as { env?: Record<string, string | undefined> }).env?.VITE_API_BASE_URL || '').trim();
  if (envBase) {
    return envBase.replace(/\/+$/, '');
  }

  if (typeof window !== 'undefined') {
    const host = window.location.hostname.toLowerCase();
    if (API_HOST_MAPPING[host]) {
      return API_HOST_MAPPING[host];
    }
  }

  return '/api';
};

export const API_BASE_URL = resolveApiBaseUrl();

const normalizeApiPath = (path: string): string => {
  if (!path) return '/';
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return normalized.startsWith('/api/') ? normalized.slice(4) : normalized;
};

export const buildApiUrl = (path: string): string => {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  return `${API_BASE_URL}${normalizeApiPath(path)}`;
};

export const getAdminToken = (): string => {
  const sessionToken = sessionStorage.getItem(ADMIN_TOKEN_KEY);
  if (sessionToken) {
    return sessionToken;
  }
  const legacyToken = localStorage.getItem(ADMIN_TOKEN_KEY);
  if (legacyToken) {
    sessionStorage.setItem(ADMIN_TOKEN_KEY, legacyToken);
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    return legacyToken;
  }
  return '';
};

export const setAdminToken = (token: string): void => {
  sessionStorage.setItem(ADMIN_TOKEN_KEY, token);
  localStorage.removeItem(ADMIN_TOKEN_KEY);
};

export const clearAdminToken = (): void => {
  sessionStorage.removeItem(ADMIN_TOKEN_KEY);
  localStorage.removeItem(ADMIN_TOKEN_KEY);
};

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = getAdminToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

api.interceptors.response.use((response) => {
  return response.data;
}, (error) => {
  if (error.response && error.response.status === 401) {
    clearAdminToken();
  }
  return Promise.reject(error);
});

export const toApiError = (error: unknown): ApiError => {
  if (axios.isAxiosError(error)) {
    return {
      message: error.message,
      status: error.response?.status,
      data: error.response?.data,
    };
  }
  if (error instanceof Error) {
    return { message: error.message };
  }
  return { message: 'Unknown error' };
};

export default api;
