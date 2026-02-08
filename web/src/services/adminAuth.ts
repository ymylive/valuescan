import api from './api';

export type AdminAuthResponse = {
  success: boolean;
  token?: string;
  user?: string;
  expires_at?: string;
  error?: string;
};

export const adminLogin = async (username: string, password: string): Promise<AdminAuthResponse> => {
  return api.post('/v1/admin/login', { username, password });
};

export const adminCheck = async (): Promise<AdminAuthResponse> => {
  return api.get('/v1/admin/check');
};

