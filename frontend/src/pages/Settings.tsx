import { useEffect, useState } from 'react';
import { settingsApi } from '../services/api';
import type { AppSettings } from '../services/api';

const CAPTCHA_MODES = [
  { value: 'auto', label: 'Automatico (local, depois 2Captcha)' },
  { value: 'local', label: 'Somente local (gratuito)' },
  { value: '2captcha', label: 'Somente 2Captcha (pago)' },
  { value: 'off', label: 'Desativado (para no captcha)' },
];

export function Settings() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [mode, setMode] = useState('auto');
  const [key, setKey] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const res = await settingsApi.get();
    setSettings(res.data);
    setMode(res.data.captcha_mode);
  };

  useEffect(() => {
    load();
  }, []);

  const save = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const payload: { captcha_mode?: string; twocaptcha_api_key?: string } = {
        captcha_mode: mode,
      };
      if (key.trim()) payload.twocaptcha_api_key = key.trim();
      const res = await settingsApi.update(payload);
      setSettings(res.data);
      setKey('');
      setMsg('Configuracoes salvas.');
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Falha ao salvar.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-slate-100 mb-4">Configuracoes</h1>

      <div className="bg-[#16213e] rounded-xl border border-purple-900/30 p-6 space-y-5">
        <div>
          <h2 className="text-lg font-semibold text-slate-100 mb-1">Captcha da pirataria</h2>
          <p className="text-sm text-slate-400">
            Como resolver o captcha que o jogo pede durante a pirataria automatica.
          </p>
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Modo</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200"
          >
            {CAPTCHA_MODES.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">
            Chave da API 2Captcha (opcional)
          </label>
          <input
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder={settings?.twocaptcha_key_set ? '•••••••• (ja configurada)' : 'Cole a chave aqui'}
            className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200"
          />
          <p className="text-[11px] text-slate-500 mt-1">
            So precisa se for usar o modo 2Captcha. Pegue em https://2captcha.com (servico pago).
          </p>
        </div>

        {settings && (
          <div className="text-xs text-slate-400 space-y-1 border-t border-slate-700/50 pt-3">
            <p>
              Resolvedor local (gratuito):{' '}
              {settings.local_captcha_available ? (
                <span className="text-green-400">disponivel</span>
              ) : (
                <span className="text-amber-400">
                  indisponivel (instale 'onnxruntime')
                </span>
              )}
            </p>
            <p>
              Chave 2Captcha:{' '}
              {settings.twocaptcha_key_set ? (
                <span className="text-green-400">configurada</span>
              ) : (
                <span className="text-slate-500">nao configurada</span>
              )}
            </p>
          </div>
        )}

        <div className="flex items-center gap-3">
          <button
            onClick={save}
            disabled={busy}
            className="px-4 py-2 rounded bg-purple-700 hover:bg-purple-600 text-white text-sm transition disabled:opacity-50"
          >
            Salvar
          </button>
          {msg && <span className="text-sm text-slate-300">{msg}</span>}
        </div>
      </div>
    </div>
  );
}
