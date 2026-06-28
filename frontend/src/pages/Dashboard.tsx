import { useEffect, useState } from 'react';
import { Users, Shield, Activity, Wifi } from 'lucide-react';
import { useStore } from '../stores/useStore';
import { statsApi, accountsApi } from '../services/api';

export function Dashboard() {
  const { stats, setStats, accounts, setAccounts } = useStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [statsRes, accountsRes] = await Promise.all([
        statsApi.get(),
        accountsApi.list(),
      ]);
      setStats(statsRes.data);
      setAccounts(accountsRes.data);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-slate-100 mb-6">Dashboard</h1>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Total Accounts"
          value={stats.total_accounts}
          icon={<Users className="w-5 h-5" />}
          color="purple"
        />
        <StatCard
          title="Online"
          value={stats.online_accounts}
          icon={<Wifi className="w-5 h-5" />}
          color="green"
        />
        <StatCard
          title="Proxies"
          value={stats.total_proxies}
          icon={<Shield className="w-5 h-5" />}
          color="blue"
        />
        <StatCard
          title="Active Tasks"
          value={stats.active_tasks}
          icon={<Activity className="w-5 h-5" />}
          color="yellow"
        />
      </div>

      {/* Recent Accounts */}
      <div className="bg-[#16213e] rounded-xl border border-purple-900/30 p-5">
        <h2 className="text-lg font-semibold text-slate-200 mb-4">Accounts</h2>
        {accounts.length === 0 ? (
          <p className="text-slate-400 text-sm">No accounts added yet. Go to Accounts to add one.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-700">
                  <th className="text-left py-2 px-3">Player</th>
                  <th className="text-left py-2 px-3">Server</th>
                  <th className="text-left py-2 px-3">Group</th>
                  <th className="text-left py-2 px-3">Status</th>
                  <th className="text-left py-2 px-3">Last Login</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account) => (
                  <tr key={account.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                    <td className="py-3 px-3 font-medium text-slate-200">{account.nickname}</td>
                    <td className="py-3 px-3 text-slate-400">
                      {account.server_country} | {account.server_world}
                    </td>
                    <td className="py-3 px-3 text-slate-400">{account.group_name}</td>
                    <td className="py-3 px-3">
                      <StatusBadge status={account.status} />
                    </td>
                    <td className="py-3 px-3 text-slate-400 text-xs">
                      {account.last_login
                        ? new Date(account.last_login).toLocaleString()
                        : 'Never'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
  color,
}: {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: string;
}) {
  const colorMap: Record<string, string> = {
    purple: 'bg-purple-900/30 text-purple-400 border-purple-700/40',
    green: 'bg-green-900/30 text-green-400 border-green-700/40',
    blue: 'bg-blue-900/30 text-blue-400 border-blue-700/40',
    yellow: 'bg-yellow-900/30 text-yellow-400 border-yellow-700/40',
  };

  return (
    <div className={`rounded-xl border p-4 ${colorMap[color]}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wider opacity-80">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
        </div>
        <div className="opacity-60">{icon}</div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const statusMap: Record<string, { bg: string; text: string }> = {
    online: { bg: 'bg-green-900/40', text: 'text-green-400' },
    offline: { bg: 'bg-slate-700/40', text: 'text-slate-400' },
    error: { bg: 'bg-red-900/40', text: 'text-red-400' },
    captcha: { bg: 'bg-yellow-900/40', text: 'text-yellow-400' },
  };

  const style = statusMap[status] || statusMap.offline;

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text}`}>
      {status}
    </span>
  );
}
