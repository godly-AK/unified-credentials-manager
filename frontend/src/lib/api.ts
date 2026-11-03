import axios from 'axios';

const api = axios.create({
  // Same-origin by default: one HTTPS address can serve the portal and API.
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || '',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
});

api.interceptors.request.use(async config => {
  const method = config.method?.toLowerCase() ?? 'get';
  if (['post', 'put', 'patch', 'delete'].includes(method) && !['/api/login', '/api/register'].includes(config.url ?? '')) {
    const profile = await api.get('/api/me');
    config.headers.set('X-UCM-CSRF', profile.data.data.csrf_token);
  }
  return config;
});

export function getApiError(error: unknown, fallback: string): string {
  if (!axios.isAxiosError(error)) return fallback;
  if (error.response?.status === 429) return 'Too many attempts. Wait a little before trying again.';
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(item => item.msg).join(' ');
  const message = error.response?.data?.message;
  return typeof message === 'string' ? message : fallback;
}

export default api;
