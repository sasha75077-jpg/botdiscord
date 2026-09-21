import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor для добавления токена
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor для обработки ошибок авторизации
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('No refresh token');
        }

        const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);

        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  ownerLogin: (email: string, password: string) =>
    api.post('/auth/owner/login', { email, password }),

  getDiscordOAuthUrl: (guildId?: string) =>
    api.get('/auth/discord/url', { params: { guild_id: guildId } }),

  discordCallback: (code: string, guildId?: string) =>
    api.post('/auth/discord/callback', { code, guild_id: guildId }),

  refreshToken: (refreshToken: string) =>
    api.post('/auth/refresh', { refresh_token: refreshToken }),

  switchGuild: (guildId: string) =>
    api.post('/auth/switch', { guild_id: guildId }),

  getCurrentUser: () => api.get('/auth/me'),
};

// Guilds API
export const guildsApi = {
  list: () => api.get('/guilds'),
  get: (guildId: string) => api.get(`/guilds/${guildId}`),
  getSettings: (guildId: string) => api.get(`/guilds/${guildId}/settings`),
  updateSettings: (guildId: string, settings: Record<string, string>) =>
    api.put(`/guilds/${guildId}/settings`, { settings }),
  getModules: (guildId: string) => api.get(`/guilds/${guildId}/modules`),
  toggleModule: (guildId: string, moduleName: string, isEnabled: boolean) =>
    api.put(`/guilds/${guildId}/modules/${moduleName}`, null, {
      params: { is_enabled: isEnabled },
    }),
  discordRoles: (guildId: string) => api.get(`/guilds/${guildId}/discord-roles`),
  family: (guildId: string) => api.get(`/guilds/${guildId}/family`),
  dashboard: (guildId: string) => api.get(`/guilds/${guildId}/dashboard`),
  discordChannels: (guildId: string) => api.get(`/guilds/${guildId}/discord-channels`),
  botLogs: (guildId: string, limit = 100) =>
    api.get(`/guilds/${guildId}/bot-logs`, { params: { limit } }),
};

// Contracts API
export const contractsApi = {
  create: (guildId: string, data: { contract_type: string; price?: number; nickname?: string; details?: Record<string, any> }) =>
    api.post(`/guilds/${guildId}/contracts/`, data),
  createMultipart: async (guildId: string, form: FormData) => {
    const base = api.defaults.baseURL || '';
    const token = localStorage.getItem('access_token');
    const resp = await fetch(`${base}/guilds/${guildId}/contracts/`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      const err: any = new Error((data as any).error || 'Ошибка отправки');
      err.response = { data };
      throw err;
    }
    return { data: await resp.json() };
  },
  list: (guildId: string, params?: any) =>
    api.get(`/guilds/${guildId}/contracts/`, { params }),
  get: (guildId: string, contractId: number) =>
    api.get(`/guilds/${guildId}/contracts/${contractId}`),
  claim: (guildId: string, contractId: number) =>
    api.post(`/guilds/${guildId}/contracts/${contractId}/claim`),
  update: (guildId: string, contractId: number, data: any) =>
    api.put(`/guilds/${guildId}/contracts/${contractId}`, data),
  delete: (guildId: string, contractId: number) =>
    api.delete(`/guilds/${guildId}/contracts/${contractId}`),
  stats: (guildId: string) => api.get(`/guilds/${guildId}/contracts/stats`),
};

// Users API
export const usersApi = {
  getMe: (guildId: string) => api.get(`/guilds/${guildId}/users/me`),
  get: (guildId: string, discordId: string) =>
    api.get(`/guilds/${guildId}/users/${discordId}`),
  getStats: (guildId: string, discordId: string) =>
    api.get(`/guilds/${guildId}/users/${discordId}/stats`),
  list: (guildId: string) => api.get(`/guilds/${guildId}/users/`),
  setMyStatic: (guildId: string, value: string) =>
    api.put(`/guilds/${guildId}/users/me`, { static: value }),
};

// Applications API
export const applicationsApi = {
  list: (guildId: string, status?: string) =>
    api.get(`/guilds/${guildId}/applications`, { params: { status } }),
  get: (guildId: string, id: number) =>
    api.get(`/guilds/${guildId}/applications/${id}`),
  create: (guildId: string, answers: Record<string, string>) =>
    api.post(`/guilds/${guildId}/applications`, { answers }),
  claim: (guildId: string, id: number) =>
    api.post(`/guilds/${guildId}/applications/${id}/claim`),
  decide: (guildId: string, id: number, accepted: boolean, reason?: string) =>
    api.post(`/guilds/${guildId}/applications/${id}/decide`, { accepted, reason }),
  messages: (guildId: string, id: number) =>
    api.get(`/guilds/${guildId}/applications/${id}/messages`),
  postMessage: (guildId: string, id: number, content: string) =>
    api.post(`/guilds/${guildId}/applications/${id}/messages`, { content }),
};

// Reports API
export const reportsApi = {
  listBonus: (guildId: string, params?: any) =>
    api.get(`/guilds/${guildId}/reports/bonus`, { params }),
  getBonus: (guildId: string, reportId: number) =>
    api.get(`/guilds/${guildId}/reports/bonus/${reportId}`),
  approveBonus: (guildId: string, reportId: number, data: any) =>
    api.put(`/guilds/${guildId}/reports/bonus/${reportId}/approve`, data),
  listPromotion: (guildId: string, params?: any) =>
    api.get(`/guilds/${guildId}/reports/promotion`, { params }),
};

// Permissions API
export const permissionsApi = {
  list: (guildId: string) =>
    api.get(`/guilds/${guildId}/permissions`),
  assign: (guildId: string, discordId: string, role: string) =>
    api.post(`/guilds/${guildId}/permissions`, { discord_id: discordId, role }),
  remove: (guildId: string, discordId: string) =>
    api.delete(`/guilds/${guildId}/permissions/${discordId}`),
  getMyRole: (guildId: string) =>
    api.get(`/guilds/${guildId}/permissions/me`),
};

// Showcase API (публичная витрина серверов)
export const showcaseApi = {
  list: (all = false) => api.get('/showcase', { params: all ? { all: 1 } : {} }),
  create: (data: any) => api.post('/showcase', data),
  update: (id: number, data: any) => api.put(`/showcase/${id}`, data),
  remove: (id: number) => api.delete(`/showcase/${id}`),
};

// Bonus API
export const bonusApi = {
  list: (guildId: string, params?: any) =>
    api.get(`/guilds/${guildId}/bonus`, { params }),
  submit: (guildId: string, week_start?: string, week_end?: string) =>
    api.post(`/guilds/${guildId}/bonus`, { week_start, week_end }),
  approve: (guildId: string, id: number) =>
    api.put(`/guilds/${guildId}/bonus/${id}/approve`),
  reject: (guildId: string, id: number, reason?: string) =>
    api.put(`/guilds/${guildId}/bonus/${id}/reject`, { reason }),
};

// Panels API (постинг панелей в Discord с сайта)
export const panelsApi = {
  enqueue: (data: { guild_id: string; panel_type: string; channel_id: string }) =>
    api.post('/panels/tasks', data),
  tasks: (guildId?: string) =>
    api.get('/panels/tasks', { params: guildId ? { guild_id: guildId } : {} }),
};

// Ranks API
export const ranksApi = {
  list: (guildId: string) => api.get(`/guilds/${guildId}/ranks`),
  create: (guildId: string, data: { name: string; role_id?: string; sort_order?: number }) =>
    api.post(`/guilds/${guildId}/ranks`, data),
  update: (guildId: string, id: number, data: { name?: string; role_id?: string | null; sort_order?: number }) =>
    api.put(`/guilds/${guildId}/ranks/${id}`, data),
  remove: (guildId: string, id: number) =>
    api.delete(`/guilds/${guildId}/ranks/${id}`),
  requirements: (guildId: string) => api.get(`/guilds/${guildId}/requirements`),
  saveRequirements: (guildId: string, data: { main?: any[]; alt?: any[] }) =>
    api.put(`/guilds/${guildId}/requirements`, data),
};

// Prices API
export const pricesApi = {
  list: () => api.get('/prices'),
  save: (items: Record<string, number>) => api.put('/prices', { items }),
};

export default api;
