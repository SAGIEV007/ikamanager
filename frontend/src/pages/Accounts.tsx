import { useEffect, useState } from 'react';
import { Plus, Trash2, LogIn, LogOut, RefreshCw, Building2, TreePine } from 'lucide-react';
import { useStore } from '../stores/useStore';
import { accountsApi, proxiesApi } from '../services/api';
import type { AccountCreate } from '../services/api';

export function Accounts() {
  const { accounts, setAccounts, setProxies } = useStore();
  const [showAddForm, setShowAddForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

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
    if (!window.__ikaBlackboxReady) {
      alert('Token blackbox nao esta pronto. Aguarde alguns segundos e tente novamente.');
      return;
    }
    setActionLoading(id);
    setActionMessage('Fazendo login na Gameforge...');
    try {
      const res = await accountsApi.login(id);
      setActionMessage(res.data.message || 'Login OK!');
      await loadData();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'object') {
        if (detail.error_type === 'CHALLENGE_REQUIRED') {
          alert('Challenge necessario. Token blackbox rejeitado. Tente recarregar a pagina.');
        } else if (detail.error_type === 'CREDENTIALS_INVALID') {
          alert('Email ou senha incorretos.');
        } else {
          alert(detail.message || 'Login falhou');
        }
      } else {
        alert(detail || 'Login falhou');
      }
    } finally {
      setActionLoading(null);
      setTimeout(() => setActionMessage(null), 5000);
    }
  };

  const handleLogout = async (id: number) => {
    setActionLoading(id);
    try {
      await accountsApi.logout(id);
      await loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Logout falhou');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Tem certeza que deseja excluir esta conta?')) return;
    try {
      await accountsApi.delete(id);
      await loadData();
    } catch (err) {
      alert('Falha ao excluir conta');
    }
  };

  const handleDonate = async (id: number) => {
    setActionLoading(id);
    setActionMessage('Executando doacao...');
    try {
      const res = await accountsApi.donate(id, 0, 'wood', 0);
      setActionMessage(res.data.message || 'Doacao realizada!');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Falha na doacao. Faca login primeiro.');
    } finally {
      setActionLoading(null);
      setTimeout(() => setActionMessage(null), 5000);
    }
  };

  const handleBuild = async (id: number) => {
    setActionLoading(id);
    setActionMessage('Iniciando construcao...');
    try {
      const res = await accountsApi.build(id, 0, 0);
      setActionMessage(res.data.message || 'Construcao iniciada!');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Falha na construcao. Faca login primeiro.');
    } finally {
      setActionLoading(null);
      setTimeout(() => setActionMessage(null), 5000);
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
        <h1 className="text-2xl font-bold text-slate-100">Contas</h1>
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center gap-2 bg-purple-700 hover:bg-purple-600 text-white px-4 py-2 rounded-lg text-sm transition"
        >
          <Plus className="w-4 h-4" />
          Adicionar Conta
        </button>
      </div>

      {/* Status message */}
      {actionMessage && (
        <div className="mb-4 p-3 bg-blue-900/30 border border-blue-700/30 rounded-lg">
          <p className="text-sm text-blue-300">{actionMessage}</p>
        </div>
      )}

      {/* Add Account Form */}
      {showAddForm && (
        <AddAccountForm
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
            <p>Nenhuma conta ainda. Clique em "Adicionar Conta" para comecar.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-400 border-b border-slate-700 bg-slate-800/30">
                <th className="text-left py-3 px-4">Jogador</th>
                <th className="text-left py-3 px-4">Servidor</th>
                <th className="text-left py-3 px-4">Status</th>
                <th className="text-right py-3 px-4">Acoes</th>
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
                    {account.server_world || account.server_country || 'Auto-detectar no login'}
                  </td>
                  <td className="py-3 px-4">
                    <StatusBadge status={account.status} message={account.status_message} />
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center justify-end gap-1">
                      {account.is_online ? (
                        <>
                          <button
                            onClick={() => handleDonate(account.id)}
                            disabled={actionLoading === account.id}
                            className="p-1.5 rounded text-green-400 hover:bg-green-900/30 transition disabled:opacity-50"
                            title="Doar recursos na ilha"
                          >
                            <TreePine className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleBuild(account.id)}
                            disabled={actionLoading === account.id}
                            className="p-1.5 rounded text-blue-400 hover:bg-blue-900/30 transition disabled:opacity-50"
                            title="Melhorar edificio"
                          >
                            <Building2 className="w-4 h-4" />
                          </button>
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
                        </>
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
                        title="Excluir"
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
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState<AccountCreate>({
    email: '',
    password: '',
    nickname: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await accountsApi.create(form);
      onCreated();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Falha ao criar conta');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-[#16213e] rounded-xl border border-purple-900/30 p-6 mb-6">
      <h2 className="text-lg font-semibold text-slate-200 mb-4">Adicionar Conta</h2>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Input
          label="Email Gameforge"
          type="email"
          value={form.email}
          onChange={(v) => setForm({ ...form, email: v })}
          placeholder="email@example.com"
          required
        />
        <Input
          label="Senha"
          type="password"
          value={form.password}
          onChange={(v) => setForm({ ...form, password: v })}
          placeholder="********"
          required
        />
        <Input
          label="Apelido (opcional)"
          value={form.nickname || ''}
          onChange={(v) => setForm({ ...form, nickname: v })}
          placeholder="Detectado automaticamente no login"
        />

        <div className="col-span-full flex justify-end gap-3 mt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 rounded-lg text-sm bg-purple-700 hover:bg-purple-600 text-white transition disabled:opacity-50"
          >
            {submitting ? 'Adicionando...' : 'Adicionar'}
          </button>
        </div>
      </form>

      <div className="mt-4 p-3 bg-slate-800/50 border border-slate-700/30 rounded-lg">
        <p className="text-xs text-slate-400">
          Apenas email e senha sao necessarios. O servidor e mundo serao detectados automaticamente quando voce fizer login.
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
  placeholder = '',
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="block text-xs text-slate-400 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-purple-500 focus:outline-none placeholder-slate-600"
      />
    </div>
  );
}

function StatusBadge({ status, message }: { status: string; message: string | null }) {
  const statusMap: Record<string, { bg: string; text: string }> = {
    online: { bg: 'bg-green-900/40', text: 'text-green-400' },
    offline: { bg: 'bg-slate-700/40', text: 'text-slate-400' },
    error: { bg: 'bg-red-900/40', text: 'text-red-400' },
  };
  const style = statusMap[status] || statusMap.offline;

  return (
    <div>
      <span className={`px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text}`}>
        {status}
      </span>
      {message && <p className="text-xs text-slate-500 mt-1 truncate max-w-[250px]">{message}</p>}
    </div>
  );
}
