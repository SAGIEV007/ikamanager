import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Account types
export interface IkariamAccount {
  id: number;
  nickname: string;
  email: string;
  server_country: string;
  server_world: string;
  server_number: number | null;
  server_language: string | null;
  group_name: string;
  is_online: boolean;
  is_active: boolean;
  status: string;
  status_message: string | null;
  last_login: string | null;
  last_action: string | null;
  gold: number;
  population: number;
  proxy_id: number | null;
  delay_min: number;
  delay_max: number;
  created_at: string;
}

export interface AccountCreate {
  email: string;
  password: string;
  nickname?: string;
  group_name?: string;
}

// Proxy types
export interface Proxy {
  id: number;
  host: string;
  port: number;
  protocol: string;
  username: string | null;
  label: string | null;
  country: string | null;
  is_active: boolean;
  is_valid: boolean;
  last_check: string | null;
  response_time_ms: number | null;
  fail_count: number;
  created_at: string;
}

export interface ProxyCreate {
  host: string;
  port: number;
  protocol?: string;
  username?: string;
  password?: string;
  label?: string;
  country?: string;
}

// Task types
export interface AutomationTask {
  id: number;
  account_id: number;
  task_type: string;
  status: string;
  schedule: string | null;
  config: Record<string, unknown>;
  last_run: string | null;
  next_run: string | null;
  run_count: number;
  error_message: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Stats {
  total_accounts: number;
  online_accounts: number;
  total_proxies: number;
  active_tasks: number;
}

// Blackbox token helper
declare global {
  interface Window {
    __ikaBlackbox: string;
    __ikaBlackboxReady: boolean;
  }
}

function getBlackbox(): string {
  return window.__ikaBlackbox || '';
}

// Game data types
export interface City {
  id: string;
  name: string;
  coords: string;
  tradegood?: string;
  relationship?: string;
}

export interface BuildingPosition {
  position: number;
  name: string;
  building: string;
  level: number | null;
  canUpgrade: boolean | null;
  isMaxLevel: boolean | null;
  isBusy: boolean;
}

export interface CityDetail {
  id: string;
  name: string;
  islandId: string;
  coords?: string;
  tradegood?: string;
  resources: Record<string, number>;
  positions: BuildingPosition[];
  error?: string;
}

// API calls
export const accountsApi = {
  list: (group?: string) => api.get<IkariamAccount[]>('/accounts/', { params: { group } }),
  get: (id: number) => api.get<IkariamAccount>(`/accounts/${id}`),
  create: (data: AccountCreate) => api.post<IkariamAccount>('/accounts/', data),
  update: (id: number, data: Partial<IkariamAccount>) => api.put<IkariamAccount>(`/accounts/${id}`, data),
  delete: (id: number) => api.delete(`/accounts/${id}`),
  login: (id: number) => api.post(`/accounts/${id}/login`, { blackbox: getBlackbox() }),
  logout: (id: number) => api.post(`/accounts/${id}/logout`),
  getCities: (id: number) => api.get<{ cities: City[] }>(`/accounts/${id}/cities`),
  getGameData: (id: number) => api.get<{ cities: CityDetail[] }>(`/accounts/${id}/game-data`),
  getCity: (id: number, cityId: string) => api.get<CityDetail>(`/accounts/${id}/city/${cityId}`),
  donate: (id: number, cityId: string, resourceType: string, amount: number) =>
    api.post(`/accounts/${id}/donate`, { city_id: cityId, resource_type: resourceType, amount }),
  build: (id: number, cityId: string, position: number) =>
    api.post(`/accounts/${id}/build`, { city_id: cityId, position }),
  piracy: (id: number, cityId: string, missionLevel: number) =>
    api.post(`/accounts/${id}/piracy`, { city_id: cityId, mission_level: missionLevel }),
};

export const proxiesApi = {
  list: () => api.get<Proxy[]>('/proxies/'),
  create: (data: ProxyCreate) => api.post<Proxy>('/proxies/', data),
  update: (id: number, data: Partial<Proxy>) => api.put<Proxy>(`/proxies/${id}`, data),
  delete: (id: number) => api.delete(`/proxies/${id}`),
  test: (id: number) => api.post(`/proxies/${id}/test`),
};

export const tasksApi = {
  list: (accountId?: number) => api.get<AutomationTask[]>('/tasks/', { params: { account_id: accountId } }),
  create: (data: { account_id: number; task_type: string; schedule?: string; config?: Record<string, unknown> }) =>
    api.post<AutomationTask>('/tasks/', data),
  update: (id: number, data: Partial<AutomationTask>) => api.put<AutomationTask>(`/tasks/${id}`, data),
  delete: (id: number) => api.delete(`/tasks/${id}`),
  start: (id: number) => api.post(`/tasks/${id}/start`),
  stop: (id: number) => api.post(`/tasks/${id}/stop`),
};

export const statsApi = {
  get: () => api.get<Stats>('/stats'),
};

export default api;
