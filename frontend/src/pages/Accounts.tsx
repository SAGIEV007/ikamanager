import { Fragment, useEffect, useState } from 'react';
import { Plus, Trash2, LogIn, LogOut, RefreshCw, MapPin, ChevronDown, ChevronRight, ShieldCheck } from 'lucide-react';
import { useStore } from '../stores/useStore';
import { accountsApi, proxiesApi, bulkApi } from '../services/api';
import type {
  AccountCreate,
  CityDetail,
  AutoPiracyStatus,
  ResourceTaskStatus,
  Proxy,
  IkariamAccount,
} from '../services/api';

export function Accounts() {
  const { accounts, setAccounts, proxies, setProxies, updateAccount } = useStore();
  const [showAddForm, setShowAddForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [verifyingId, setVerifyingId] = useState<number | null>(null);

  useEffect(() => {
    loadData();
    // Light refresh from our own DB (no game requests) so statuses updated by
    // the background tasks — like "session expired" — show up quickly instead
    // of arriving late.
    const t = setInterval(() => loadAccountsOnly(), 8000);
    return () => clearInterval(t);
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

  const loadAccountsOnly = async () => {
    try {
      const res = await accountsApi.list();
      setAccounts(res.data);
    } catch {
      // ignore transient refresh errors
    }
  };

  // Ask the server to actually confirm each session against the game and sync
  // the real status. This is the honest check (vs. trusting a stale "online").
  const verifyAll = async () => {
    setVerifying(true);
    setActionMessage('Verificando sessões reais das contas...');
    try {
      await bulkApi.verify([]);
      await loadAccountsOnly();
      setActionMessage('Sessões verificadas.');
    } catch {
      setActionMessage('Falha ao verificar sessões.');
    } finally {
      setVerifying(false);
      setTimeout(() => setActionMessage(null), 4000);
    }
  };

  const verifyOne = async (id: number) => {
    setVerifyingId(id);
    try {
      await accountsApi.verifySession(id);
      await loadAccountsOnly();
    } catch {
      setActionMessage('Falha ao verificar a sessão desta conta.');
    } finally {
      setVerifyingId(null);
    }
  };

  const tryManualToken = async (id: number) => {
    const instructions =
      'A Gameforge exigiu um desafio que nao foi possivel passar automaticamente.\n\n' +
      'Alternativa (como no Ikabot): cole o token manual.\n\n' +
      '1) Entre em https://lobby.ikariam.gameforge.com/ pelo navegador e faca login\n' +
      '2) Pressione F12, abra a aba "Console"\n' +
      "3) Cole e execute: document.cookie.split(';').forEach(x => {if (x.includes('production')) console.log(x)})\n" +
      '4) Copie o valor de gf-token-production e cole aqui abaixo:';
    const token = window.prompt(instructions, '');
    if (!token || !token.trim()) {
      alert('Login cancelado. Nenhum token informado.');
      return;
    }
    try {
      setActionMessage('Entrando com token manual...');
      const res = await accountsApi.login(id, token.trim());
      setActionMessage(res.data.message || 'Login OK!');
      await loadData();
    } catch (e: any) {
      const d = e.response?.data?.detail;
      alert((typeof d === 'object' ? d.message : d) || 'Token invalido ou expirado.');
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
      const errorType = typeof detail === 'object' ? detail.error_type : undefined;
      if (errorType === 'CHALLENGE_REQUIRED' || errorType === 'CREDENTIALS_INVALID') {
        await tryManualToken(id);
      } else if (typeof detail === 'object') {
        alert(detail.message || 'Login falhou');
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
        <div className="flex items-center gap-2">
          <button
            onClick={verifyAll}
            disabled={verifying}
            className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-slate-100 px-3 py-2 rounded-lg text-sm transition disabled:opacity-50"
            title="Confirma quais contas estão realmente logadas no jogo agora"
          >
            <ShieldCheck className={`w-4 h-4 ${verifying ? 'animate-pulse' : ''}`} />
            {verifying ? 'Verificando...' : 'Verificar sessões'}
          </button>
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 bg-purple-700 hover:bg-purple-600 text-white px-4 py-2 rounded-lg text-sm transition"
          >
            <Plus className="w-4 h-4" />
            Adicionar Conta
          </button>
        </div>
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

      {/* Multi-account (bulk) controls */}
      {accounts.length > 0 && <MultiAccountPanel />}

      {/* Live status of every running donation/upgrade across all accounts */}
      {accounts.length > 0 && <RunningTasksPanel />}

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
                <th className="text-left py-3 px-4">Proxy</th>
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
                    <ProxySelect
                      value={account.proxy_id}
                      proxies={proxies}
                      onChange={async (proxyId) => {
                        updateAccount(account.id, { proxy_id: proxyId });
                        try {
                          await accountsApi.update(account.id, { proxy_id: proxyId });
                        } catch {
                          setActionMessage('Falha ao salvar proxy da conta.');
                        }
                      }}
                    />
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
                        onClick={() => verifyOne(account.id)}
                        disabled={verifyingId === account.id}
                        className="p-1.5 rounded text-sky-300 hover:bg-sky-900/30 transition disabled:opacity-50"
                        title="Verificar se esta conta está realmente logada no jogo agora"
                      >
                        <ShieldCheck
                          className={`w-4 h-4 ${verifyingId === account.id ? 'animate-pulse' : ''}`}
                        />
                      </button>
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
                    <td colSpan={5} className="p-4">
                      <OperationHoursControl account={account} />
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

function MultiAccountPanel() {
  const { accounts, proxies } = useStore();
  const online = accounts.filter((a) => a.is_online);
  const [selected, setSelected] = useState<number[]>([]);
  const [resource, setResource] = useState('wood');
  const [mode, setMode] = useState<'amount' | 'percent'>('percent');
  const [amount, setAmount] = useState('1000');
  const [percent, setPercent] = useState('50');
  const [donateInterval, setDonateInterval] = useState('30');
  const [upgradeInterval, setUpgradeInterval] = useState('20');
  const [msg, setMsg] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  const toggle = (id: number) =>
    setSelected((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  const allSelected = online.length > 0 && selected.length === online.length;
  const toggleAll = () => setSelected(allSelected ? [] : online.map((a) => a.id));

  const report = (r: { started: number[]; skipped: { account_id: number; reason: string }[] }) => {
    const parts = [`${r.started.length} iniciada(s)`];
    if (r.skipped?.length) {
      parts.push(
        `${r.skipped.length} ignorada(s): ` +
          r.skipped.map((s) => `#${s.account_id} (${s.reason})`).join(', ')
      );
    }
    setMsg(parts.join(' — '));
  };

  const startDonate = async () => {
    if (selected.length === 0) return setMsg('Selecione ao menos uma conta.');
    setMsg('Iniciando doações...');
    try {
      const res = await bulkApi.startDonate(selected, {
        city_id: '',
        resource_type: resource,
        amount: mode === 'amount' ? parseInt(amount || '0', 10) : 0,
        percent: mode === 'percent' ? parseInt(percent || '0', 10) : 0,
        interval_minutes: parseInt(donateInterval || '30', 10),
        runs: 0,
      });
      report(res.data);
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Falha ao iniciar doações.');
    }
  };

  const startUpgrade = async () => {
    if (selected.length === 0) return setMsg('Selecione ao menos uma conta.');
    setMsg('Iniciando upgrades...');
    try {
      const res = await bulkApi.startUpgrade(selected, {
        city_id: '',
        position: null,
        interval_minutes: parseInt(upgradeInterval || '20', 10),
        runs: 0,
      });
      report(res.data);
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Falha ao iniciar upgrades.');
    }
  };

  const stopAll = async () => {
    if (selected.length === 0) return setMsg('Selecione ao menos uma conta.');
    try {
      await Promise.all([bulkApi.stopDonate(selected), bulkApi.stopUpgrade(selected)]);
      setMsg('Tarefas paradas nas contas selecionadas.');
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Falha ao parar.');
    }
  };

  const proxyOf = (id: number) => {
    const acc = accounts.find((a) => a.id === id);
    if (!acc?.proxy_id) return 'sem proxy';
    const p = proxies.find((x) => x.id === acc.proxy_id);
    return p ? `proxy: ${p.label || p.host}` : 'sem proxy';
  };

  return (
    <div className="bg-[#16213e] rounded-xl border border-purple-900/30 p-4 mb-6">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 text-sm font-semibold text-purple-200"
      >
        {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        Multiconta — recursos em várias contas ao mesmo tempo
        <span className="text-xs text-slate-500">({online.length} online)</span>
      </button>

      {open && (
        <div className="mt-4 space-y-4">
          {online.length === 0 ? (
            <p className="text-xs text-slate-400">
              Nenhuma conta online. Faça login nas contas para operá-las em conjunto.
            </p>
          ) : (
            <>
              {/* Account selection */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <button
                    onClick={toggleAll}
                    className="text-xs px-2 py-1 rounded bg-slate-800 text-slate-200 hover:bg-slate-700"
                  >
                    {allSelected ? 'Desmarcar todas' : 'Selecionar todas'}
                  </button>
                  <span className="text-xs text-slate-500">{selected.length} selecionada(s)</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-1">
                  {online.map((a) => (
                    <label
                      key={a.id}
                      className="flex items-center gap-2 px-2 py-1 rounded bg-slate-900/60 text-xs text-slate-200 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selected.includes(a.id)}
                        onChange={() => toggle(a.id)}
                      />
                      <span className="truncate">{a.nickname}</span>
                      <span className="ml-auto text-[10px] text-slate-500">{proxyOf(a.id)}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Bulk donate */}
              <div className="bg-slate-800/40 rounded-lg p-3">
                <p className="text-xs font-medium text-emerald-300 mb-2">
                  Doação automática (todas as selecionadas)
                </p>
                <div className="flex items-end gap-2 flex-wrap">
                  <div>
                    <label className="block text-[10px] text-slate-500 mb-1">Recurso</label>
                    <select
                      value={resource}
                      onChange={(e) => setResource(e.target.value)}
                      className="bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200"
                    >
                      <option value="wood">Madeira (floresta)</option>
                      <option value="tradegood">Bem de luxo (ilha)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-500 mb-1">Modo</label>
                    <select
                      value={mode}
                      onChange={(e) => setMode(e.target.value as 'amount' | 'percent')}
                      className="bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200"
                    >
                      <option value="percent">% do estoque</option>
                      <option value="amount">Quantidade fixa</option>
                    </select>
                  </div>
                  {mode === 'amount' ? (
                    <div>
                      <label className="block text-[10px] text-slate-500 mb-1">Quantidade</label>
                      <input
                        type="number"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        className="w-24 bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200"
                      />
                    </div>
                  ) : (
                    <div>
                      <label className="block text-[10px] text-slate-500 mb-1">%</label>
                      <input
                        type="number"
                        min={1}
                        max={100}
                        value={percent}
                        onChange={(e) => setPercent(e.target.value)}
                        className="w-16 bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200"
                      />
                    </div>
                  )}
                  <div>
                    <label className="block text-[10px] text-slate-500 mb-1">A cada (min)</label>
                    <input
                      type="number"
                      min={1}
                      value={donateInterval}
                      onChange={(e) => setDonateInterval(e.target.value)}
                      className="w-20 bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200"
                    />
                  </div>
                  <button
                    onClick={startDonate}
                    className="px-3 py-1.5 rounded bg-emerald-700 hover:bg-emerald-600 text-white text-xs transition"
                  >
                    Iniciar doações
                  </button>
                </div>
              </div>

              {/* Bulk upgrade */}
              <div className="bg-slate-800/40 rounded-lg p-3">
                <p className="text-xs font-medium text-sky-300 mb-2">
                  Upgrade automático de edifícios (todas as selecionadas)
                </p>
                <div className="flex items-end gap-2 flex-wrap">
                  <div>
                    <label className="block text-[10px] text-slate-500 mb-1">Tentar a cada (min)</label>
                    <input
                      type="number"
                      min={1}
                      value={upgradeInterval}
                      onChange={(e) => setUpgradeInterval(e.target.value)}
                      className="w-20 bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200"
                    />
                  </div>
                  <button
                    onClick={startUpgrade}
                    className="px-3 py-1.5 rounded bg-sky-700 hover:bg-sky-600 text-white text-xs transition"
                  >
                    Iniciar upgrades
                  </button>
                  <button
                    onClick={stopAll}
                    className="px-3 py-1.5 rounded bg-orange-700 hover:bg-orange-600 text-white text-xs transition"
                  >
                    Parar tudo (selecionadas)
                  </button>
                </div>
                <p className="text-[10px] text-slate-500 mt-1">
                  Usa a cidade principal de cada conta automaticamente. Para escolher uma cidade
                  específica, use os controles dentro de cada conta.
                </p>
              </div>

              {msg && <p className="text-xs text-blue-300">{msg}</p>}
            </>
          )}
        </div>
      )}
    </div>
  );
}

const RES_SHORT: Record<string, string> = {
  wood: 'madeira',
  tradegood: 'luxo',
};

function summarizeTask(t: ResourceTaskStatus): string {
  const cfg = t.config || {};
  const intervalMin = cfg.interval_s ? Math.round(Number(cfg.interval_s) / 60) : null;
  if (t.kind === 'donate') {
    const res = RES_SHORT[String(cfg.resource_type)] || String(cfg.resource_type ?? '');
    const qty =
      Number(cfg.percent) > 0
        ? `${cfg.percent}% do estoque`
        : `${Number(cfg.amount || 0).toLocaleString('pt-BR')} un`;
    return `${qty} de ${res}${intervalMin ? ` · a cada ~${intervalMin}min` : ''}`;
  }
  if (t.kind === 'upgrade') {
    const where = cfg.position != null ? `posição ${cfg.position}` : 'escolha inteligente';
    return `${where}${intervalMin ? ` · tenta a cada ~${intervalMin}min` : ''}`;
  }
  return '';
}

const STATE_STYLES: Record<string, { label: string; cls: string }> = {
  running: { label: 'Rodando', cls: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/50' },
  waiting_hours: { label: 'Fora do horário', cls: 'bg-amber-900/40 text-amber-300 border-amber-700/50' },
  waiting_login: { label: 'Aguardando login', cls: 'bg-sky-900/40 text-sky-300 border-sky-700/50' },
  error: { label: 'Erro', cls: 'bg-red-900/40 text-red-300 border-red-700/50' },
  done: { label: 'Concluído', cls: 'bg-slate-700/40 text-slate-300 border-slate-600/50' },
  stopped: { label: 'Parado', cls: 'bg-slate-700/40 text-slate-400 border-slate-600/50' },
};

function StateChip({ state, running }: { state: string; running: boolean }) {
  const key = !running && state === 'running' ? 'stopped' : state;
  const s = STATE_STYLES[key] || { label: state, cls: 'bg-slate-700/40 text-slate-300 border-slate-600/50' };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] border ${s.cls}`}>
      {s.label}
    </span>
  );
}

function countdown(nextRunAt: number | null, now: number): string {
  if (!nextRunAt) return '—';
  const secs = Math.max(0, Math.round(nextRunAt - now / 1000));
  if (secs <= 0) return 'agora';
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  if (m >= 60) {
    const h = Math.floor(m / 60);
    return `${h}h${m % 60}min`;
  }
  return m > 0 ? `${m}min ${s}s` : `${s}s`;
}

function RunningTasksPanel() {
  const { accounts, proxies } = useStore();
  const [tasks, setTasks] = useState<ResourceTaskStatus[]>([]);
  const [now, setNow] = useState(Date.now());
  const [busyStop, setBusyStop] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const res = await bulkApi.status();
      setTasks(res.data.tasks || []);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 3000);
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      clearInterval(t);
      clearInterval(tick);
    };
  }, []);

  const nameOf = (id: number) => accounts.find((a) => a.id === id)?.nickname || `#${id}`;
  const proxyOf = (id: number) => {
    const acc = accounts.find((a) => a.id === id);
    if (!acc?.proxy_id) return null;
    const p = proxies.find((x) => x.id === acc.proxy_id);
    return p ? p.label || p.host : null;
  };

  const stopOne = async (kind: string, accountId: number) => {
    const key = `${kind}-${accountId}`;
    setBusyStop(key);
    try {
      if (kind === 'donate') await bulkApi.stopDonate([accountId]);
      else if (kind === 'upgrade') await bulkApi.stopUpgrade([accountId]);
      await refresh();
    } catch {
      /* ignore */
    } finally {
      setBusyStop(null);
    }
  };

  const active = tasks.filter((t) => t.kind === 'donate' || t.kind === 'upgrade');
  const donateCount = active.filter((t) => t.kind === 'donate' && t.running).length;
  const upgradeCount = active.filter((t) => t.kind === 'upgrade' && t.running).length;

  if (active.length === 0) return null;

  return (
    <div className="bg-[#16213e] rounded-xl border border-purple-900/30 p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-purple-200">Ações em andamento</h2>
        <span className="text-xs text-slate-500">
          {donateCount} doação(ões) · {upgradeCount} upgrade(s) rodando
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-slate-500 border-b border-slate-700/60">
              <th className="text-left py-2 pr-3">Conta</th>
              <th className="text-left py-2 pr-3">Ação</th>
              <th className="text-left py-2 pr-3">Configuração</th>
              <th className="text-left py-2 pr-3">Estado</th>
              <th className="text-right py-2 pr-3">Ciclos</th>
              <th className="text-right py-2 pr-3">Próximo</th>
              <th className="text-right py-2">—</th>
            </tr>
          </thead>
          <tbody>
            {active.map((t) => {
              const id = t.account_id ?? -1;
              const proxy = proxyOf(id);
              const key = `${t.kind}-${id}`;
              return (
                <tr key={key} className="border-b border-slate-800/60">
                  <td className="py-2 pr-3">
                    <div className="text-slate-200">{nameOf(id)}</div>
                    <div className="text-[10px] text-slate-500">
                      {proxy ? `proxy: ${proxy}` : 'sem proxy'}
                    </div>
                  </td>
                  <td className="py-2 pr-3">
                    <span
                      className={
                        t.kind === 'donate' ? 'text-emerald-300' : 'text-sky-300'
                      }
                    >
                      {t.kind === 'donate' ? 'Doação' : 'Upgrade'}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-slate-400">{summarizeTask(t)}</td>
                  <td className="py-2 pr-3">
                    <StateChip state={t.state} running={!!t.running} />
                    {(t.state === 'error' || t.last_result === 'failed') && t.last_message && (
                      <div className="text-[10px] text-red-400 mt-0.5 max-w-[220px] truncate" title={t.last_message}>
                        {t.last_message}
                      </div>
                    )}
                  </td>
                  <td className="py-2 pr-3 text-right text-slate-300">
                    {t.runs_done}
                    {t.runs ? `/${t.runs}` : ''}
                  </td>
                  <td className="py-2 pr-3 text-right text-slate-300">
                    {t.running ? countdown(t.next_run_at, now) : '—'}
                  </td>
                  <td className="py-2 text-right">
                    {t.running && (
                      <button
                        onClick={() => stopOne(t.kind || '', id)}
                        disabled={busyStop === key}
                        className="px-2 py-1 rounded bg-orange-800/60 hover:bg-orange-700 text-orange-200 text-[10px] transition disabled:opacity-50"
                      >
                        Parar
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function OperationHoursControl({ account }: { account: IkariamAccount }) {
  const { updateAccount } = useStore();
  // start == end means "no restriction" (24h). Enabled when they differ.
  const enabled = account.operation_start_hour !== account.operation_end_hour;
  const [start, setStart] = useState(String(account.operation_start_hour ?? 0));
  const [end, setEnd] = useState(String(account.operation_end_hour ?? 0));
  const [msg, setMsg] = useState<string | null>(null);

  const save = async (s: number, e: number) => {
    setMsg(null);
    updateAccount(account.id, { operation_start_hour: s, operation_end_hour: e });
    try {
      await accountsApi.update(account.id, {
        operation_start_hour: s,
        operation_end_hour: e,
      });
    } catch {
      setMsg('Falha ao salvar horário.');
    }
  };

  const toggle = (on: boolean) => {
    if (!on) {
      // Disable = 24h (start == end).
      save(0, 0);
    } else {
      // Enable with a sensible default window if currently 24h.
      const s = 6;
      const e = 23;
      setStart(String(s));
      setEnd(String(e));
      save(s, e);
    }
  };

  return (
    <div className="bg-slate-800/40 rounded-lg p-3 mb-4">
      <div className="flex items-center gap-3 flex-wrap">
        <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => toggle(e.target.checked)}
          />
          Limitar horário de operação
        </label>
        {enabled ? (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>das</span>
            <input
              type="number"
              min={0}
              max={23}
              value={start}
              onChange={(e) => setStart(e.target.value)}
              onBlur={() => save(parseInt(start || '0', 10), parseInt(end || '0', 10))}
              className="w-14 bg-slate-900 border border-slate-600 rounded px-2 py-1 text-slate-200"
            />
            <span>h às</span>
            <input
              type="number"
              min={0}
              max={23}
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              onBlur={() => save(parseInt(start || '0', 10), parseInt(end || '0', 10))}
              className="w-14 bg-slate-900 border border-slate-600 rounded px-2 py-1 text-slate-200"
            />
            <span>h</span>
          </div>
        ) : (
          <span className="text-xs text-slate-500">
            Sem restrição (roda 24h). Marque para definir uma janela.
          </span>
        )}
        {msg && <span className="text-xs text-red-400">{msg}</span>}
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

  const runDonate = async (resourceType: string, amount: number, percent: number) => {
    if (!city) return;
    setBusy(true);
    setMsg('Executando doacao...');
    try {
      const res = await accountsApi.donate(accountId, city.id, resourceType, amount, percent);
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
            <p className="text-xs font-medium text-slate-300 mb-2">Doar na ilha (uma vez)</p>
            <DonateForm disabled={busy} onDonate={runDonate} />
          </div>

          {/* Recurring donation (island upgrade bot) */}
          <AutoDonatePanel accountId={accountId} cityId={city.id} />

          {/* Recurring building upgrade */}
          <AutoUpgradePanel accountId={accountId} cityId={city.id} />

          {/* Piracy (only if the city has a pirate fortress) */}
          {city.positions.some((p) => p.building === 'pirateFortress') && (
            <div className="bg-slate-800/40 rounded-lg p-3">
              <p className="text-xs font-medium text-slate-300 mb-2">Pirataria (fortaleza pirata)</p>
              <PiracyForm
                accountId={accountId}
                cityId={city.id}
                disabled={busy}
                onStart={runPiracy}
              />
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
  onDonate: (resourceType: string, amount: number, percent: number) => void;
}) {
  const [type, setType] = useState('wood');
  const [mode, setMode] = useState<'amount' | 'percent'>('amount');
  const [amount, setAmount] = useState('1000');
  const [percent, setPercent] = useState('50');

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
        <label className="block text-[10px] text-slate-500 mb-1">Modo</label>
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as 'amount' | 'percent')}
          className="bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200"
        >
          <option value="amount">Quantidade fixa</option>
          <option value="percent">% do estoque</option>
        </select>
      </div>
      {mode === 'amount' ? (
        <div>
          <label className="block text-[10px] text-slate-500 mb-1">Quantidade</label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-28 bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200"
          />
        </div>
      ) : (
        <div>
          <label className="block text-[10px] text-slate-500 mb-1">% do estoque</label>
          <input
            type="number"
            min={1}
            max={100}
            value={percent}
            onChange={(e) => setPercent(e.target.value)}
            className="w-24 bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200"
          />
        </div>
      )}
      <button
        onClick={() =>
          mode === 'amount'
            ? onDonate(type, parseInt(amount || '0', 10), 0)
            : onDonate(type, 0, parseInt(percent || '0', 10))
        }
        disabled={disabled}
        className="px-3 py-1.5 rounded bg-green-700 hover:bg-green-600 text-white text-xs transition disabled:opacity-50"
      >
        Doar
      </button>
    </div>
  );
}

function TaskStatusLine({
  running,
  detail,
}: {
  running: boolean;
  detail: ResourceTaskStatus | null;
}) {
  if (!detail) return null;
  return (
    <p className="text-xs text-blue-300 mt-2">
      {running ? '\u25B6 ' : ''}
      {detail.runs_done} ciclo(s){detail.runs ? `/${detail.runs}` : ''} — {detail.message}
    </p>
  );
}

function AutoDonatePanel({ accountId, cityId }: { accountId: number; cityId: string }) {
  const [type, setType] = useState('wood');
  const [mode, setMode] = useState<'amount' | 'percent'>('percent');
  const [amount, setAmount] = useState('1000');
  const [percent, setPercent] = useState('50');
  const [interval, setIntervalMin] = useState('30');
  const [running, setRunning] = useState(false);
  const [detail, setDetail] = useState<ResourceTaskStatus | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const res = await accountsApi.autoDonateStatus(accountId);
      setRunning(res.data.running);
      setDetail(res.data.detail);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [accountId]);

  const start = async () => {
    setErr(null);
    try {
      await accountsApi.startAutoDonate(accountId, {
        city_id: cityId,
        resource_type: type,
        amount: mode === 'amount' ? parseInt(amount || '0', 10) : 0,
        percent: mode === 'percent' ? parseInt(percent || '0', 10) : 0,
        interval_minutes: parseInt(interval || '30', 10),
        runs: 0,
      });
      await refresh();
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Falha ao iniciar doacao automatica.');
    }
  };

  const stop = async () => {
    try {
      await accountsApi.stopAutoDonate(accountId);
      await refresh();
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Falha ao parar.');
    }
  };

  return (
    <div className="bg-slate-800/40 rounded-lg p-3">
      <p className="text-xs font-medium text-emerald-300 mb-2">
        Doação automática (bot de ilha)
      </p>
      <div className="flex items-end gap-2 flex-wrap">
        <div>
          <label className="block text-[10px] text-slate-500 mb-1">Recurso</label>
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            disabled={running}
            className="bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200 disabled:opacity-50"
          >
            <option value="wood">Madeira (floresta)</option>
            <option value="tradegood">Bem de luxo (ilha)</option>
          </select>
        </div>
        <div>
          <label className="block text-[10px] text-slate-500 mb-1">Modo</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as 'amount' | 'percent')}
            disabled={running}
            className="bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200 disabled:opacity-50"
          >
            <option value="percent">% do estoque</option>
            <option value="amount">Quantidade fixa</option>
          </select>
        </div>
        {mode === 'amount' ? (
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Quantidade</label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              disabled={running}
              className="w-24 bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200 disabled:opacity-50"
            />
          </div>
        ) : (
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">%</label>
            <input
              type="number"
              min={1}
              max={100}
              value={percent}
              onChange={(e) => setPercent(e.target.value)}
              disabled={running}
              className="w-16 bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200 disabled:opacity-50"
            />
          </div>
        )}
        <div>
          <label className="block text-[10px] text-slate-500 mb-1">A cada (min)</label>
          <input
            type="number"
            min={1}
            value={interval}
            onChange={(e) => setIntervalMin(e.target.value)}
            disabled={running}
            className="w-20 bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200 disabled:opacity-50"
          />
        </div>
        {running ? (
          <button
            onClick={stop}
            className="px-3 py-1.5 rounded bg-orange-700 hover:bg-orange-600 text-white text-xs transition"
          >
            Parar
          </button>
        ) : (
          <button
            onClick={start}
            className="px-3 py-1.5 rounded bg-emerald-700 hover:bg-emerald-600 text-white text-xs transition"
          >
            Iniciar
          </button>
        )}
      </div>
      <p className="text-[10px] text-slate-500 mt-1">
        Doa repetidamente com tempos aleatórios (respeita a janela de horário, se você ativar).
        "% do estoque" nunca falha por falta de recurso.
      </p>
      {err && <p className="text-xs text-red-400">{err}</p>}
      <TaskStatusLine running={running} detail={detail} />
    </div>
  );
}

function AutoUpgradePanel({ accountId, cityId }: { accountId: number; cityId: string }) {
  const [interval, setIntervalMin] = useState('20');
  const [running, setRunning] = useState(false);
  const [detail, setDetail] = useState<ResourceTaskStatus | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const res = await accountsApi.autoUpgradeStatus(accountId);
      setRunning(res.data.running);
      setDetail(res.data.detail);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [accountId]);

  const start = async () => {
    setErr(null);
    try {
      await accountsApi.startAutoUpgrade(accountId, {
        city_id: cityId,
        position: null,
        interval_minutes: parseInt(interval || '20', 10),
        runs: 0,
      });
      await refresh();
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Falha ao iniciar upgrade automatico.');
    }
  };

  const stop = async () => {
    try {
      await accountsApi.stopAutoUpgrade(accountId);
      await refresh();
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Falha ao parar.');
    }
  };

  return (
    <div className="bg-slate-800/40 rounded-lg p-3">
      <p className="text-xs font-medium text-sky-300 mb-2">Upgrade automático de edifícios</p>
      <div className="flex items-end gap-2 flex-wrap">
        <div>
          <label className="block text-[10px] text-slate-500 mb-1">Tentar a cada (min)</label>
          <input
            type="number"
            min={1}
            value={interval}
            onChange={(e) => setIntervalMin(e.target.value)}
            disabled={running}
            className="w-20 bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200 disabled:opacity-50"
          />
        </div>
        {running ? (
          <button
            onClick={stop}
            className="px-3 py-1.5 rounded bg-orange-700 hover:bg-orange-600 text-white text-xs transition"
          >
            Parar
          </button>
        ) : (
          <button
            onClick={start}
            className="px-3 py-1.5 rounded bg-sky-700 hover:bg-sky-600 text-white text-xs transition"
          >
            Iniciar
          </button>
        )}
      </div>
      <p className="text-[10px] text-slate-500 mt-1">
        A cada ciclo escolhe de forma inteligente o próximo edifício a subir — mantém a cidade
        equilibrada priorizando depósito, prefeitura, satisfação e produção. Respeita horário e
        recursos; quando não dá, espera o próximo ciclo.
      </p>
      {err && <p className="text-xs text-red-400">{err}</p>}
      <TaskStatusLine running={running} detail={detail} />
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
  accountId,
  cityId,
  disabled,
  onStart,
}: {
  accountId: number;
  cityId: string;
  disabled: boolean;
  onStart: (missionLevel: number) => void;
}) {
  const [level, setLevel] = useState('1');
  const [runs, setRuns] = useState('10');
  const [extraWait, setExtraWait] = useState('30');
  const [auto, setAuto] = useState<AutoPiracyStatus | null>(null);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const refreshStatus = async () => {
    try {
      const res = await accountsApi.autoPiracyStatus(accountId);
      setRunning(res.data.running);
      setAuto(res.data.detail);
    } catch {
      /* ignore polling errors */
    }
  };

  useEffect(() => {
    refreshStatus();
    const t = setInterval(refreshStatus, 5000);
    return () => clearInterval(t);
  }, [accountId]);

  const startAuto = async () => {
    setErr(null);
    try {
      await accountsApi.startAutoPiracy(
        accountId,
        cityId,
        parseInt(level, 10),
        parseInt(runs || '1', 10),
        parseInt(extraWait || '0', 10)
      );
      await refreshStatus();
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Falha ao iniciar pirataria automatica.');
    }
  };

  const stopAuto = async () => {
    try {
      await accountsApi.stopAutoPiracy(accountId);
      await refreshStatus();
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Falha ao parar.');
    }
  };

  return (
    <div className="space-y-3">
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
          disabled={disabled || running}
          className="px-3 py-1.5 rounded bg-red-800/70 hover:bg-red-700 text-white text-xs transition disabled:opacity-50"
        >
          Rodar 1x
        </button>
      </div>

      <div className="border-t border-slate-700/50 pt-3">
        <p className="text-[11px] font-medium text-slate-300 mb-2">Automatico (repetir sozinho)</p>
        <div className="flex items-end gap-2 flex-wrap">
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Quantas vezes</label>
            <input
              type="number"
              min={1}
              value={runs}
              onChange={(e) => setRuns(e.target.value)}
              disabled={running}
              className="w-20 bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200 disabled:opacity-50"
            />
          </div>
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Espera extra (s)</label>
            <input
              type="number"
              min={0}
              value={extraWait}
              onChange={(e) => setExtraWait(e.target.value)}
              disabled={running}
              className="w-24 bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-200 disabled:opacity-50"
            />
          </div>
          {running ? (
            <button
              onClick={stopAuto}
              className="px-3 py-1.5 rounded bg-orange-700 hover:bg-orange-600 text-white text-xs transition"
            >
              Parar
            </button>
          ) : (
            <button
              onClick={startAuto}
              disabled={disabled}
              className="px-3 py-1.5 rounded bg-red-700 hover:bg-red-600 text-white text-xs transition disabled:opacity-50"
            >
              Iniciar automatico
            </button>
          )}
        </div>
        <p className="text-[10px] text-slate-500 mt-1">
          Espera a duracao da missao + tempo aleatorio (0 ate o valor acima) antes de repetir.
        </p>
      </div>

      {err && <p className="text-xs text-red-400">{err}</p>}
      {auto && (
        <p className="text-xs text-blue-300">
          {running ? '▶ ' : ''}
          {auto.runs_done}/{auto.runs} missoes — {auto.message}
        </p>
      )}
      <p className="text-[10px] text-slate-500">
        Missoes longas podem exigir captcha; nesse caso o automatico para e avisa (resolver captcha automatico e um passo futuro).
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

function ProxySelect({
  value,
  proxies,
  onChange,
}: {
  value: number | null;
  proxies: Proxy[];
  onChange: (proxyId: number | null) => void;
}) {
  return (
    <select
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value ? parseInt(e.target.value, 10) : null)}
      className={`bg-slate-900 border rounded px-2 py-1 text-xs ${
        value ? 'border-slate-600 text-slate-200' : 'border-amber-700/50 text-amber-300'
      }`}
      title="Proxy usado por esta conta"
    >
      <option value="">sem proxy</option>
      {proxies.map((p) => (
        <option key={p.id} value={p.id}>
          {p.label || `${p.host}:${p.port}`}
        </option>
      ))}
    </select>
  );
}

const STATUS_META: Record<string, { bg: string; text: string; label: string }> = {
  online: { bg: 'bg-green-900/40', text: 'text-green-400', label: 'Online' },
  offline: { bg: 'bg-slate-700/40', text: 'text-slate-400', label: 'Offline' },
  error: { bg: 'bg-red-900/40', text: 'text-red-400', label: 'Erro' },
  session_expired: {
    bg: 'bg-amber-900/40',
    text: 'text-amber-300',
    label: 'Sessão expirada — relogar',
  },
  checking: { bg: 'bg-sky-900/40', text: 'text-sky-300', label: 'Verificando…' },
  captcha: { bg: 'bg-amber-900/40', text: 'text-amber-300', label: 'Captcha' },
};

function StatusBadge({ status, message }: { status: string; message: string | null }) {
  const meta = STATUS_META[status] || STATUS_META.offline;

  return (
    <div>
      <span className={`px-2 py-0.5 rounded text-xs font-medium ${meta.bg} ${meta.text}`}>
        {meta.label}
      </span>
      {message && <p className="text-xs text-slate-500 mt-1 truncate max-w-[250px]">{message}</p>}
    </div>
  );
}
