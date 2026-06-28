import { useEffect, useState } from 'react';
import { Plus, Trash2, LogIn, LogOut, RefreshCw } from 'lucide-react';
import { useStore } from '../stores/useStore';
import { accountsApi, proxiesApi } from '../services/api';
import type { AccountCreate, Proxy } from '../services/api';

export function Accounts() {
  const { accounts, setAccounts, proxies, setProxies } = useStore();
  const [showAddForm, setShowAddForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [accountsRes, proxiesRes] = await Promise.all([
        accountsApi.list(),
        proxiesApi.list(),
      ]);
      setAccounts(accountsRes.data);
      setProxies(proxiesRes.data);
    } catch (err) {
      console.error('Failed to load accounts:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (id: number) => {
    setActionLoading(id);
    try {
      await accountsApi.login(id);
      await loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Login failed');
    } finally {
      setActionLoading(null);
    }
  };

  const handleLogout = async (id: number) => {
    setActionLoading(id);
    try {
      await accountsApi.logout(id);
      await loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Logout failed');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this account?')) return;
    try {
      await accountsApi.delete(id);
      await loadData();
    } catch (err) {
      alert('Failed to delete account');
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
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-100">Accounts</h1>
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center gap-2 bg-purple-700 hover:bg-purple-600 text-white px-4 py-2 rounded-lg text-sm transition"
        >
          <Plus className="w-4 h-4" />
          Add Account
        </button>
      </div>

      {/* Add Account Form */}
      {showAddForm && (
        <AddAccountForm
          proxies={proxies}
          onClose={() => setShowAddForm(false)}
          onCreated={() => {
            setShowAddForm(false);
            loadData();
          }}
        />
      )}

      {/* Accounts Table */}
      <div className="bg-[#16213e] rounded-xl border border-purple-900/30 overflow-hidden">
        {accounts.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <p>No accounts yet. Click "Add Account" to get started.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-400 border-b border-slate-700 bg-slate-800/30">
                <th className="text-left py-3 px-4">Player</th>
                <th className="text-left py-3 px-4">Server</th>
                <th className="text-left py-3 px-4">Group</th>
                <th className="text-left py-3 px-4">Status</th>
                <th className="text-left py-3 px-4">Proxy</th>
                <th className="text-right py-3 px-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((account) => (
                <tr key={account.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                  <td className="py-3 px-4">
                    <div>
                      <p className="font-medium text-slate-200">{account.nickname}</p>
                      <p className="text-xs text-slate-500">{account.email}</p>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-slate-400">
                    {account.server_country} | {account.server_world}
                  </td>
                  <td className="py-3 px-4 text-slate-400">{account.group_name}</td>
                  <td className="py-3 px-4">
                    <StatusBadge status={account.status} message={account.status_message} />
                  </td>
                  <td className="py-3 px-4 text-slate-400 text-xs">
                    {account.proxy_id ? `Proxy #${account.proxy_id}` : 'No proxy'}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center justify-end gap-2">
                      {account.is_online ? (
                        <button
                          onClick={() => handleLogout(account.id)}
                          disabled={actionLoading === account.id}
                          className="p-1.5 rounded text-orange-400 hover:bg-orange-900/30 transition disabled:opacity-50"
                          title="Logout"
                        >
                          {actionLoading === account.id ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                          ) : (
                            <LogOut className="w-4 h-4" />
                          )}
                        </button>
                      ) : (
                        <button
                          onClick={() => handleLogin(account.id)}
                          disabled={actionLoading === account.id}
                          className="p-1.5 rounded text-green-400 hover:bg-green-900/30 transition disabled:opacity-50"
                          title="Login"
                        >
                          {actionLoading === account.id ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                          ) : (
                            <LogIn className="w-4 h-4" />
                          )}
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(account.id)}
                        className="p-1.5 rounded text-red-400 hover:bg-red-900/30 transition"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function AddAccountForm({
  proxies,
  onClose,
  onCreated,
}: {
  proxies: Proxy[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState<AccountCreate>({
    nickname: '',
    email: '',
    password: '',
    server_country: '',
    server_world: '',
    group_name: 'Default',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await accountsApi.create(form);
      onCreated();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create account');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-[#16213e] rounded-xl border border-purple-900/30 p-6 mb-6">
      <h2 className="text-lg font-semibold text-slate-200 mb-4">Add Account</h2>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Input
          label="Nickname"
          value={form.nickname}
          onChange={(v) => setForm({ ...form, nickname: v })}
          required
        />
        <Input
          label="Email"
          type="email"
          value={form.email}
          onChange={(v) => setForm({ ...form, email: v })}
          required
        />
        <Input
          label="Password"
          type="password"
          value={form.password}
          onChange={(v) => setForm({ ...form, password: v })}
          required
        />
        <Input
          label="Country (e.g., BR, US, GB)"
          value={form.server_country}
          onChange={(v) => setForm({ ...form, server_country: v })}
          required
        />
        <Input
          label="World (e.g., Alpha, Beta)"
          value={form.server_world}
          onChange={(v) => setForm({ ...form, server_world: v })}
          required
        />
        <Input
          label="Group"
          value={form.group_name || ''}
          onChange={(v) => setForm({ ...form, group_name: v })}
        />
        <div>
          <label className="block text-xs text-slate-400 mb-1">Proxy</label>
          <select
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200"
            value={form.proxy_id || ''}
            onChange={(e) => setForm({ ...form, proxy_id: e.target.value ? Number(e.target.value) : undefined })}
          >
            <option value="">No proxy</option>
            {proxies.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label || `${p.host}:${p.port}`} ({p.protocol})
              </option>
            ))}
          </select>
        </div>

        <div className="col-span-full flex justify-end gap-3 mt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 rounded-lg text-sm bg-purple-700 hover:bg-purple-600 text-white transition disabled:opacity-50"
          >
            {submitting ? 'Adding...' : 'Add Account'}
          </button>
        </div>
      </form>

      <div className="mt-4 p-3 bg-yellow-900/20 border border-yellow-700/30 rounded-lg">
        <p className="text-xs text-yellow-400">
          ⚠️ For your account security, use a dedicated proxy for each account. Never use the same
          IP for two accounts in the same world.
        </p>
      </div>
    </div>
  );
}

function Input({
  label,
  value,
  onChange,
  type = 'text',
  required = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <div>
      <label className="block text-xs text-slate-400 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-purple-500 focus:outline-none"
      />
    </div>
  );
}

function StatusBadge({ status, message }: { status: string; message: string | null }) {
  const statusMap: Record<string, { bg: string; text: string }> = {
    online: { bg: 'bg-green-900/40', text: 'text-green-400' },
    offline: { bg: 'bg-slate-700/40', text: 'text-slate-400' },
    error: { bg: 'bg-red-900/40', text: 'text-red-400' },
    captcha: { bg: 'bg-yellow-900/40', text: 'text-yellow-400' },
  };
  const style = statusMap[status] || statusMap.offline;

  return (
    <div>
      <span className={`px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text}`}>
        {status}
      </span>
      {message && <p className="text-xs text-slate-500 mt-1 truncate max-w-[200px]">{message}</p>}
    </div>
  );
}
