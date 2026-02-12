import axios from 'axios';

export type ApiError = {
  message: string;
  status?: number;
  data?: unknown;
};

const ADMIN_TOKEN_KEY = 'token';

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
  baseURL: '/api',
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
