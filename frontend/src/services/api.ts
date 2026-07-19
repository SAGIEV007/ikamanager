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
  operation_start_hour: number;
  operation_end_hour: number;
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
  login: (id: number, gfToken?: string) =>
    api.post(`/accounts/${id}/login`, { blackbox: getBlackbox(), gf_token: gfToken || '' }),
  logout: (id: number) => api.post(`/accounts/${id}/logout`),
  getCities: (id: number) => api.get<{ cities: City[] }>(`/accounts/${id}/cities`),
  getGameData: (id: number) => api.get<{ cities: CityDetail[] }>(`/accounts/${id}/game-data`),
  getCity: (id: number, cityId: string) => api.get<CityDetail>(`/accounts/${id}/city/${cityId}`),
  donate: (id: number, cityId: string, resourceType: string, amount: number, percent = 0) =>
    api.post(`/accounts/${id}/donate`, {
      city_id: cityId,
      resource_type: resourceType,
      amount,
      percent,
    }),
  build: (id: number, cityId: string, position: number) =>
    api.post(`/accounts/${id}/build`, { city_id: cityId, position }),
  // Recurring donations (island upgrade bot)
  startAutoDonate: (id: number, cfg: AutoDonateConfig) =>
    api.post(`/accounts/${id}/donate/auto/start`, cfg),
  stopAutoDonate: (id: number) => api.post(`/accounts/${id}/donate/auto/stop`),
  autoDonateStatus: (id: number) =>
    api.get<{ running: boolean; detail: ResourceTaskStatus | null }>(
      `/accounts/${id}/donate/auto/status`
    ),
  // Recurring building upgrades
  startAutoUpgrade: (id: number, cfg: AutoUpgradeConfig) =>
    api.post(`/accounts/${id}/upgrade/auto/start`, cfg),
  stopAutoUpgrade: (id: number) => api.post(`/accounts/${id}/upgrade/auto/stop`),
  autoUpgradeStatus: (id: number) =>
    api.get<{ running: boolean; detail: ResourceTaskStatus | null }>(
      `/accounts/${id}/upgrade/auto/status`
    ),
  piracy: (id: number, cityId: string, missionLevel: number) =>
    api.post(`/accounts/${id}/piracy`, { city_id: cityId, mission_level: missionLevel }),
  startAutoPiracy: (
    id: number,
    cityId: string,
    missionLevel: number,
    runs: number,
    extraWaitMax: number
  ) =>
    api.post(`/accounts/${id}/piracy/auto/start`, {
      city_id: cityId,
      mission_level: missionLevel,
      runs,
      extra_wait_max: extraWaitMax,
    }),
  stopAutoPiracy: (id: number) => api.post(`/accounts/${id}/piracy/auto/stop`),
  autoPiracyStatus: (id: number) =>
    api.get<{ running: boolean; detail: AutoPiracyStatus | null }>(
      `/accounts/${id}/piracy/auto/status`
    ),
};

export interface AutoDonateConfig {
  city_id: string;
  resource_type: string;
  amount?: number;
  percent?: number;
  interval_minutes?: number;
  extra_wait_max?: number;
  runs?: number;
}

export interface AutoUpgradeConfig {
  city_id: string;
  position?: number | null;
  interval_minutes?: number;
  extra_wait_max?: number;
  runs?: number;
}

export interface ResourceTaskStatus {
  state: string;
  kind?: string;
  account_id?: number;
  running?: boolean;
  runs: number;
  runs_done: number;
  next_run_at: number | null;
  message: string;
  last_result?: string;
  last_message?: string;
  config?: Record<string, unknown>;
}

export const bulkApi = {
  startDonate: (accountIds: number[], cfg: AutoDonateConfig) =>
    api.post('/bulk/donate/auto/start', { account_ids: accountIds, ...cfg }),
  stopDonate: (accountIds: number[]) =>
    api.post('/bulk/donate/auto/stop', { account_ids: accountIds }),
  startUpgrade: (accountIds: number[], cfg: AutoUpgradeConfig) =>
    api.post('/bulk/upgrade/auto/start', { account_ids: accountIds, ...cfg }),
  stopUpgrade: (accountIds: number[]) =>
    api.post('/bulk/upgrade/auto/stop', { account_ids: accountIds }),
  status: () => api.get<{ tasks: ResourceTaskStatus[] }>('/bulk/resources/status'),
};

export interface AutoPiracyStatus {
  state: string;
  city_id: string;
  mission_level: number;
  runs: number;
  runs_done: number;
  runs_left: number;
  extra_wait_max: number;
  next_run_at: number | null;
  message: string;
}

export interface AppSettings {
  captcha_mode: string;
  twocaptcha_key_set: boolean;
  local_captcha_available: boolean;
}

export const settingsApi = {
  get: () => api.get<AppSettings>('/settings/'),
  update: (data: { captcha_mode?: string; twocaptcha_api_key?: string }) =>
    api.put<AppSettings>('/settings/', data),
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
