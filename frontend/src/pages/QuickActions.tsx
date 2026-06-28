import { useEffect, useState } from 'react';
import { Skull, Swords, Package, Landmark, Ship, Sparkles, RefreshCw } from 'lucide-react';
import { useStore } from '../stores/useStore';
import { accountsApi } from '../services/api';

export function QuickActions() {
  const { accounts, setAccounts } = useStore();
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState<string | null>(null);
  const [groupFilter, setGroupFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const res = await accountsApi.list();
      setAccounts(res.data);
    } catch (err) {
      console.error('Failed to load accounts:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (id: number) => {
    const next = new Set(selected);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelected(next);
  };

  const selectAll = () => {
    if (selected.size === filteredAccounts.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(filteredAccounts.map((a) => a.id)));
    }
  };

  const groups = [...new Set(accounts.map((a) => a.group_name))];

  const filteredAccounts = accounts.filter((a) => {
    if (groupFilter && a.group_name !== groupFilter) return false;
    if (searchQuery && !a.nickname.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const executeAction = async (action: string) => {
    if (selected.size === 0) {
      alert('Select at least one account');
      return;
    }
    setExecuting(action);
    // In a real implementation, this would call the backend
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setExecuting(null);
    alert(`Action "${action}" queued for ${selected.size} account(s). Check Activities for status.`);
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
      <h1 className="text-2xl font-bold text-slate-100 mb-6">Quick Actions</h1>

      {/* Filters */}
      <div className="flex items-center gap-4 mb-4">
        <input
          type="text"
          placeholder="Search accounts..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-purple-500 focus:outline-none w-64"
        />
        <select
          value={groupFilter}
          onChange={(e) => setGroupFilter(e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200"
        >
          <option value="">All Groups</option>
          {groups.map((g) => (
            <option key={g} value={g}>{g}</option>
          ))}
        </select>
        <span className="text-sm text-slate-400">
          {selected.size} of {filteredAccounts.length} selected
        </span>
      </div>

      {/* Accounts Table with Quick Action Buttons */}
      <div className="bg-[#16213e] rounded-xl border border-purple-900/30 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-400 border-b border-slate-700 bg-slate-800/30">
              <th className="py-3 px-4">
                <input
                  type="checkbox"
                  checked={selected.size === filteredAccounts.length && filteredAccounts.length > 0}
                  onChange={selectAll}
                  className="rounded"
                />
              </th>
              <th className="text-left py-3 px-4">Group</th>
              <th className="text-left py-3 px-4">Player</th>
              <th className="text-left py-3 px-4">Quick Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredAccounts.map((account) => (
              <tr key={account.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                <td className="py-3 px-4">
                  <input
                    type="checkbox"
                    checked={selected.has(account.id)}
                    onChange={() => toggleSelect(account.id)}
                    className="rounded"
                  />
                </td>
                <td className="py-3 px-4 text-slate-400">{account.group_name}</td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${account.is_online ? 'bg-green-400' : 'bg-slate-500'}`} />
                    <span className="text-slate-200 font-medium">{account.nickname}</span>
                    <span className="text-xs text-slate-500">{account.server_world}</span>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <ActionButton label="START CAPTURE" color="green" onClick={() => executeAction('capture')} />
                    <ActionButton label="RAID" color="red" onClick={() => executeAction('raid')} />
                    <ActionButton label="ARMY" color="orange" onClick={() => executeAction('army')} />
                    <ActionButton label="RESOURCES" color="blue" onClick={() => executeAction('resources')} />
                    <ActionButton label="TRADING POST" color="purple" onClick={() => executeAction('trade')} />
                    <ActionButton label="WONDER" color="yellow" onClick={() => executeAction('wonder')} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Bulk Actions */}
      {selected.size > 0 && (
        <div className="mt-4 bg-purple-900/20 border border-purple-700/30 rounded-xl p-4">
          <p className="text-sm text-purple-300 mb-3">
            Execute for {selected.size} selected account(s):
          </p>
          <div className="flex flex-wrap gap-2">
            <BulkButton icon={<Skull className="w-4 h-4" />} label="Start Piracy" onClick={() => executeAction('piracy')} loading={executing === 'piracy'} />
            <BulkButton icon={<Swords className="w-4 h-4" />} label="Raid" onClick={() => executeAction('raid')} loading={executing === 'raid'} />
            <BulkButton icon={<Package className="w-4 h-4" />} label="Collect Resources" onClick={() => executeAction('collect')} loading={executing === 'collect'} />
            <BulkButton icon={<Landmark className="w-4 h-4" />} label="Donate" onClick={() => executeAction('donate')} loading={executing === 'donate'} />
            <BulkButton icon={<Ship className="w-4 h-4" />} label="Send Resources" onClick={() => executeAction('send')} loading={executing === 'send'} />
            <BulkButton icon={<Sparkles className="w-4 h-4" />} label="Activate Wonder" onClick={() => executeAction('wonder')} loading={executing === 'wonder'} />
          </div>
        </div>
      )}
    </div>
  );
}

function ActionButton({ label, color, onClick }: { label: string; color: string; onClick: () => void }) {
  const colorMap: Record<string, string> = {
    green: 'bg-green-800/40 text-green-400 hover:bg-green-800/60',
    red: 'bg-red-800/40 text-red-400 hover:bg-red-800/60',
    orange: 'bg-orange-800/40 text-orange-400 hover:bg-orange-800/60',
    blue: 'bg-blue-800/40 text-blue-400 hover:bg-blue-800/60',
    purple: 'bg-purple-800/40 text-purple-400 hover:bg-purple-800/60',
    yellow: 'bg-yellow-800/40 text-yellow-400 hover:bg-yellow-800/60',
  };

  return (
    <button
      onClick={onClick}
      className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider transition ${colorMap[color]}`}
    >
      {label}
    </button>
  );
}

function BulkButton({
  icon,
  label,
  onClick,
  loading,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  loading: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="flex items-center gap-2 bg-purple-700/50 hover:bg-purple-700 text-purple-200 px-3 py-2 rounded-lg text-xs transition disabled:opacity-50"
    >
      {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : icon}
      {label}
    </button>
  );
}
