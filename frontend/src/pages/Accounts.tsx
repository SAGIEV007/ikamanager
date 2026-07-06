import { Fragment, useEffect, useState } from 'react';
import { Plus, Trash2, LogIn, LogOut, RefreshCw, MapPin, ChevronDown, ChevronRight } from 'lucide-react';
import { useStore } from '../stores/useStore';
import { accountsApi, proxiesApi } from '../services/api';
import type { AccountCreate, CityDetail } from '../services/api';

export function Accounts() {
  const { accounts, setAccounts, setProxies } = useStore();
  const [showAddForm, setShowAddForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);

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

  const toggleExpand = (id: number) => {
    setExpanded((cur) => (cur === id ? null : id));
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
                <Fragment key={account.id}>
                <tr className="border-b border-slate-800 hover:bg-slate-800/30">
                  <td className="py-3 px-4">
                    <div>
                      <p className="font-medium text-slate-200">{account.nickname}</p>
                      <p className="text-xs text-slate-500">{account.email}</p>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-slate-400">
                    {account.server_world
                      ? `${account.server_world}${account.server_country ? ' (' + account.server_country + ')' : ''}`
                      : 'Auto-detectar no login'}
                  </td>
                  <td className="py-3 px-4">
                    <StatusBadge status={account.status} message={account.status_message} />
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center justify-end gap-1">
                      {account.is_online ? (
                        <>
                          <button
                            onClick={() => toggleExpand(account.id)}
                            className="flex items-center gap-1 px-2 py-1.5 rounded text-purple-300 hover:bg-purple-900/30 transition text-xs"
                            title="Ver cidades e executar acoes"
                          >
                            {expanded === account.id ? (
                              <ChevronDown className="w-4 h-4" />
                            ) : (
                              <ChevronRight className="w-4 h-4" />
                            )}
                            <MapPin className="w-4 h-4" />
                            Cidades
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
                {expanded === account.id && account.is_online && (
                  <tr className="border-b border-slate-800 bg-slate-900/40">
                    <td colSpan={4} className="p-4">
                      <CityManager accountId={account.id} />
                    </td>
                  </tr>
                )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

const RESOURCE_LABELS: Record<string, string> = {
  wood: 'Madeira',
  wine: 'Vinho',
  marble: 'Marmore',
  crystal: 'Cristal',
  sulfur: 'Enxofre',
};

function CityManager({ accountId }: { accountId: number }) {
  const [cities, setCities] = useState<CityDetail[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await accountsApi.getGameData(accountId);
      setCities(res.data.cities);
      if (res.data.cities.length > 0) setSelected(res.data.cities[0].id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Falha ao carregar cidades.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [accountId]);

  const city = cities?.find((c) => c.id === selected) || null;

  const runDonate = async (resourceType: string, amount: number) => {
    if (!city) return;
    setBusy(true);
    setMsg('Executando doacao...');
    try {
      const res = await accountsApi.donate(accountId, city.id, resourceType, amount);
      setMsg(res.data.message || 'Doacao concluida.');
      await load();
    } catch (err: any) {
      setMsg(err.response?.data?.detail || 'Falha na doacao.');
    } finally {
      setBusy(false);
    }
  };

  const runBuild = async (position: number) => {
    if (!city) return;
    setBusy(true);
    setMsg('Iniciando melhoria...');
    try {
      const res = await accountsApi.build(accountId, city.id, position);
      setMsg(res.data.message || 'Melhoria iniciada.');
      await load();
    } catch (err: any) {
      setMsg(err.response?.data?.detail || 'Falha na melhoria.');
    } finally {
      setBusy(false);
    }
  };

  const runPiracy = async (missionLevel: number) => {
    if (!city) return;
    setBusy(true);
    setMsg('Iniciando pirataria...');
    try {
      const res = await accountsApi.piracy(accountId, city.id, missionLevel);
      setMsg(res.data.message || 'Pirataria iniciada.');
    } catch (err: any) {
      setMsg(err.response?.data?.detail || 'Falha na pirataria.');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-slate-400">Carregando cidades...</p>;
  }

  if (error) {
    return (
      <div className="text-sm">
        <p className="text-red-400 mb-2">{error}</p>
        <button onClick={load} className="text-purple-300 hover:underline">
          Tentar novamente
        </button>
      </div>
    );
  }

  if (!cities || cities.length === 0) {
    return <p className="text-sm text-slate-400">Nenhuma cidade encontrada.</p>;
  }

  return (
    <div className="space-y-4">
      {/* City selector */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-slate-400">Cidade:</span>
        {cities.map((c) => (
          <button
            key={c.id}
            onClick={() => setSelected(c.id)}
            className={`px-3 py-1.5 rounded-lg text-xs transition ${
              selected === c.id
                ? 'bg-purple-700 text-white'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {c.name} {c.coords ? <span className="opacity-60">{c.coords}</span> : null}
          </button>
        ))}
        <button onClick={load} className="ml-auto text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1">
          <RefreshCw className="w-3 h-3" /> Atualizar
        </button>
      </div>

      {msg && <p className="text-sm text-blue-300">{msg}</p>}

      {city && city.error && (
        <p className="text-sm text-red-400">Erro ao ler esta cidade: {city.error}</p>
      )}

      {city && !city.error && (
        <>
          {/* Resources */}
          <div className="flex gap-4 flex-wrap text-xs">
            {Object.entries(city.resources || {}).map(([k, v]) => (
              <span key={k} className="text-slate-300">
                <span className="text-slate-500">{RESOURCE_LABELS[k] || k}:</span>{' '}
                {v.toLocaleString('pt-BR')}
              </span>
            ))}
          </div>

          {/* Donation */}
          <div className="bg-slate-800/40 rounded-lg p-3">
            <p className="text-xs font-medium text-slate-300 mb-2">Doar na ilha</p>
            <DonateForm disabled={busy} onDonate={runDonate} />
          </div>

          {/* Piracy (only if the city has a pirate fortress) */}
          {city.positions.some((p) => p.building === 'pirateFortress') && (
            <div className="bg-slate-800/40 rounded-lg p-3">
              <p className="text-xs font-medium text-slate-300 mb-2">Pirataria (fortaleza pirata)</p>
              <PiracyForm disabled={busy} onStart={runPiracy} />
            </div>
          )}

          {/* Buildings */}
          <div className="bg-slate-800/40 rounded-lg p-3">
            <p className="text-xs font-medium text-slate-300 mb-2">Edificios (melhorar)</p>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
              {city.positions
                .filter((p) => p.building !== 'empty')
                .map((p) => (
                  <button
                    key={p.position}
                    onClick={() => runBuild(p.position)}
                    disabled={busy || p.isBusy || p.isMaxLevel === true}
                    className="flex items-center justify-between gap-2 px-2 py-1.5 rounded bg-slate-900/60 hover:bg-blue-900/30 text-xs text-slate-200 transition disabled:opacity-40"
                    title={p.isBusy ? 'Ja em construcao' : p.isMaxLevel ? 'Nivel maximo' : 'Melhorar'}
                  >
                    <span className="truncate">{p.name}</span>
                    <span className="text-slate-400">nv {p.level ?? '-'}</span>
                  </button>
                ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function DonateForm({
  disabled,
  onDonate,
}: {
  disabled: boolean;
  onDonate: (resourceType: string, amount: number) => void;
}) {
  const [type, setType] = useState('wood');
  const [amount, setAmount] = useState('1000');

  return (
    <div className="flex items-end gap-2 flex-wrap">
      <div>
        <label className="block text-[10px] text-slate-500 mb-1">Recurso</label>
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200"
        >
          <option value="wood">Madeira (floresta)</option>
          <option value="tradegood">Bem de luxo (ilha)</option>
        </select>
      </div>
      <div>
        <label className="block text-[10px] text-slate-500 mb-1">Quantidade</label>
        <input
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="w-28 bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200"
        />
      </div>
      <button
        onClick={() => onDonate(type, parseInt(amount || '0', 10))}
        disabled={disabled}
        className="px-3 py-1.5 rounded bg-green-700 hover:bg-green-600 text-white text-xs transition disabled:opacity-50"
      >
        Doar
      </button>
    </div>
  );
}

const PIRACY_MISSIONS = [
  { level: 1, label: '2m 30s' },
  { level: 2, label: '7m 30s' },
  { level: 3, label: '15m' },
  { level: 4, label: '30m' },
  { level: 5, label: '1h' },
  { level: 6, label: '2h' },
  { level: 7, label: '4h' },
  { level: 8, label: '8h' },
  { level: 9, label: '16h' },
];

function PiracyForm({
  disabled,
  onStart,
}: {
  disabled: boolean;
  onStart: (missionLevel: number) => void;
}) {
  const [level, setLevel] = useState('1');

  return (
    <div className="flex items-end gap-2 flex-wrap">
      <div>
        <label className="block text-[10px] text-slate-500 mb-1">Missao</label>
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          className="bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200"
        >
          {PIRACY_MISSIONS.map((m) => (
            <option key={m.level} value={m.level}>
              {m.label}
            </option>
          ))}
        </select>
      </div>
      <button
        onClick={() => onStart(parseInt(level, 10))}
        disabled={disabled}
        className="px-3 py-1.5 rounded bg-red-700 hover:bg-red-600 text-white text-xs transition disabled:opacity-50"
      >
        Iniciar pirataria
      </button>
      <p className="text-[10px] text-slate-500 basis-full">
        Missoes longas podem exigir captcha (ainda nao automatizado).
      </p>
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
