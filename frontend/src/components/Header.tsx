import { Menu, Bell, RefreshCw } from 'lucide-react';
import { useStore } from '../stores/useStore';

export function Header() {
  const { toggleSidebar, stats } = useStore();

  return (
    <header className="h-14 bg-[#16213e] border-b border-purple-900/30 flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <button
          onClick={toggleSidebar}
          className="text-slate-400 hover:text-slate-200 transition"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="text-sm text-purple-300 font-medium">
          {stats.online_accounts > 0 && (
            <span className="bg-green-900/40 text-green-400 px-2 py-1 rounded text-xs mr-2">
              {stats.online_accounts} online
            </span>
          )}
          <span className="text-slate-400">
            {stats.total_accounts} accounts • {stats.total_proxies} proxies • {stats.active_tasks} tasks
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button className="text-slate-400 hover:text-slate-200 transition p-2 rounded-lg hover:bg-slate-700/50">
          <RefreshCw className="w-4 h-4" />
        </button>
        <button className="text-slate-400 hover:text-slate-200 transition p-2 rounded-lg hover:bg-slate-700/50">
          <Bell className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
