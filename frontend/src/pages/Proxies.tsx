import { useEffect, useState } from 'react';
import { Plus, Trash2, Play, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import { useStore } from '../stores/useStore';
import { proxiesApi } from '../services/api';
import type { ProxyCreate } from '../services/api';

export function Proxies() {
  const { proxies, setProxies } = useStore();
  const [showAddForm, setShowAddForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<Record<number, { status: string; ip?: string; error?: string }>>({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const res = await proxiesApi.list();
      setProxies(res.data);
    } catch (err) {
      console.error('Failed to load proxies:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async (id: number) => {
    setTesting(id);
    try {
      const res = await proxiesApi.test(id);
      setTestResult({ ...testResult, [id]: res.data });
      await loadData();
    } catch (err) {
      setTestResult({ ...testResult, [id]: { status: 'failed', error: 'Request failed' } });
    } finally {
      setTesting(null);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this proxy?')) return;
    try {
      await proxiesApi.delete(id);
      await loadData();
    } catch (err) {
      alert('Failed to delete proxy');
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
        <h1 className="text-2xl font-bold text-slate-100">Proxies</h1>
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center gap-2 bg-purple-700 hover:bg-purple-600 text-white px-4 py-2 rounded-lg text-sm transition"
        >
          <Plus className="w-4 h-4" />
          Add Proxy
        </button>
      </div>

      {showAddForm && (
        <AddProxyForm
          onClose={() => setShowAddForm(false)}
          onCreated={() => {
            setShowAddForm(false);
            loadData();
          }}
        />
      )}

      <div className="bg-[#16213e] rounded-xl border border-purple-900/30 overflow-hidden">
        {proxies.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <p>No proxies configured. Add a proxy to protect your accounts.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-400 border-b border-slate-700 bg-slate-800/30">
                <th className="text-left py-3 px-4">Label</th>
                <th className="text-left py-3 px-4">Host:Port</th>
                <th className="text-left py-3 px-4">Protocol</th>
                <th className="text-left py-3 px-4">Status</th>
                <th className="text-left py-3 px-4">Response</th>
                <th className="text-right py-3 px-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {proxies.map((proxy) => (
                <tr key={proxy.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                  <td className="py-3 px-4 text-slate-200">{proxy.label || '-'}</td>
                  <td className="py-3 px-4 text-slate-300 font-mono text-xs">
                    {proxy.host}:{proxy.port}
                  </td>
                  <td className="py-3 px-4 text-slate-400 uppercase text-xs">{proxy.protocol}</td>
                  <td className="py-3 px-4">
                    {proxy.is_valid ? (
                      <span className="flex items-center gap-1 text-green-400 text-xs">
                        <CheckCircle className="w-3.5 h-3.5" /> Valid
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-red-400 text-xs">
                        <XCircle className="w-3.5 h-3.5" /> Invalid
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-slate-400 text-xs">
                    {proxy.response_time_ms ? `${proxy.response_time_ms.toFixed(0)}ms` : '-'}
                    {testResult[proxy.id] && (
                      <span className="ml-2 text-green-400">
                        {testResult[proxy.id].ip && `IP: ${testResult[proxy.id].ip}`}
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleTest(proxy.id)}
                        disabled={testing === proxy.id}
                        className="p-1.5 rounded text-blue-400 hover:bg-blue-900/30 transition disabled:opacity-50"
                        title="Test Proxy"
                      >
                        {testing === proxy.id ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <Play className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => handleDelete(proxy.id)}
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

function AddProxyForm({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState<ProxyCreate>({
    host: '',
    port: 0,
    protocol: 'https',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await proxiesApi.create(form);
      onCreated();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to add proxy');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-[#16213e] rounded-xl border border-purple-900/30 p-6 mb-6">
      <h2 className="text-lg font-semibold text-slate-200 mb-4">Add Proxy</h2>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <label className="block text-xs text-slate-400 mb-1">Host / IP</label>
          <input
            type="text"
            value={form.host}
            onChange={(e) => setForm({ ...form, host: e.target.value })}
            placeholder="192.168.1.1"
            required
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-purple-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1">Port</label>
          <input
            type="number"
            value={form.port || ''}
            onChange={(e) => setForm({ ...form, port: Number(e.target.value) })}
            placeholder="8080"
            required
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-purple-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1">Protocol</label>
          <select
            value={form.protocol}
            onChange={(e) => setForm({ ...form, protocol: e.target.value })}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200"
          >
            <option value="https">HTTPS</option>
            <option value="socks5">SOCKS5</option>
            <option value="socks4">SOCKS4</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1">Label (optional)</label>
          <input
            type="text"
            value={form.label || ''}
            onChange={(e) => setForm({ ...form, label: e.target.value })}
            placeholder="My Proxy"
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-purple-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1">Username (optional)</label>
          <input
            type="text"
            value={form.username || ''}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-purple-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1">Password (optional)</label>
          <input
            type="password"
            value={form.password || ''}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-purple-500 focus:outline-none"
          />
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
            {submitting ? 'Adding...' : 'Add Proxy'}
          </button>
        </div>
      </form>
    </div>
  );
}
