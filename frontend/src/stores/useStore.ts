import { create } from 'zustand';
import type { IkariamAccount, Proxy, AutomationTask, Stats } from '../services/api';

interface AppState {
  // Accounts
  accounts: IkariamAccount[];
  selectedAccount: IkariamAccount | null;
  setAccounts: (accounts: IkariamAccount[]) => void;
  setSelectedAccount: (account: IkariamAccount | null) => void;
  updateAccount: (id: number, data: Partial<IkariamAccount>) => void;

  // Proxies
  proxies: Proxy[];
  setProxies: (proxies: Proxy[]) => void;

  // Tasks
  tasks: AutomationTask[];
  setTasks: (tasks: AutomationTask[]) => void;

  // Stats
  stats: Stats;
  setStats: (stats: Stats) => void;

  // UI
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  currentPage: string;
  setCurrentPage: (page: string) => void;

  // Logs
  logs: LogEntry[];
  addLog: (log: LogEntry) => void;
  clearLogs: () => void;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  account_id: number;
  action: string;
  message: string;
  level: 'info' | 'warning' | 'error' | 'success';
}

export const useStore = create<AppState>((set) => ({
  // Accounts
  accounts: [],
  selectedAccount: null,
  setAccounts: (accounts) => set({ accounts }),
  setSelectedAccount: (account) => set({ selectedAccount: account }),
  updateAccount: (id, data) =>
    set((state) => ({
      accounts: state.accounts.map((a) => (a.id === id ? { ...a, ...data } : a)),
    })),

  // Proxies
  proxies: [],
  setProxies: (proxies) => set({ proxies }),

  // Tasks
  tasks: [],
  setTasks: (tasks) => set({ tasks }),

  // Stats
  stats: { total_accounts: 0, online_accounts: 0, total_proxies: 0, active_tasks: 0 },
  setStats: (stats) => set({ stats }),

  // UI
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  currentPage: 'dashboard',
  setCurrentPage: (page) => set({ currentPage: page }),

  // Logs
  logs: [],
  addLog: (log) => set((state) => ({ logs: [log, ...state.logs].slice(0, 200) })),
  clearLogs: () => set({ logs: [] }),
}));
