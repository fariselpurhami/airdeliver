'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

type MemoryExport = {
    enabled: boolean;
    retention_days: number;
    preferences: { category: string; value: string; created_at: string; expires_at: string }[];
};

export default function CustomerMemoryControls() {
    const [memory, setMemory] = useState<MemoryExport | null>(null);
    const [busy, setBusy] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [confirmDelete, setConfirmDelete] = useState(false);
    const [exportText, setExportText] = useState<string | null>(null);

    const load = async () => {
        const { data } = await api.get<MemoryExport>('/users/me/memory');
        if (!data || typeof data.enabled !== 'boolean' || !Array.isArray(data.preferences)) throw new Error('Invalid memory response');
        setMemory(data);
    };
    useEffect(() => {
        let active = true;
        api.get<MemoryExport>('/users/me/memory').then(({ data }) => {
            if (!active) return;
            if (!data || typeof data.enabled !== 'boolean' || !Array.isArray(data.preferences)) throw new Error('Invalid memory response');
            setMemory(data);
        }).catch(() => { if (active) setError('Shopping memory could not be loaded. No settings were changed.'); })
            .finally(() => { if (active) setBusy(false); });
        return () => { active = false; };
    }, []);

    const changeConsent = async (enabled: boolean) => {
        if (busy) return;
        setBusy(true);setError(null);setExportText(null);
        try {
            if (enabled) await api.put('/users/me/memory/consent', { enabled: true });
            else await api.delete('/users/me/memory');
            await load();
            setConfirmDelete(false);
        } catch {
            setError('The memory change could not be confirmed. Refresh these settings before trying again.');
        } finally { setBusy(false); }
    };
    const refresh = async () => {
        setBusy(true);setError(null);
        try { await load(); } catch { setError('Shopping memory could not be loaded. No settings were changed.'); }
        finally { setBusy(false); }
    };
    const exportMemory = async () => {
        setBusy(true);setError(null);
        try {
            const { data } = await api.get<MemoryExport>('/users/me/memory');
            setExportText(JSON.stringify(data, null, 2));
        } catch { setError('Your memory export could not be loaded. Try refreshing these settings.'); }
        finally { setBusy(false); }
    };

    return (
        <section aria-labelledby="shopping-memory-heading" className="mt-10 w-full rounded-2xl border border-white/20 bg-zinc-950/95 p-5 text-left text-white">
            <h2 id="shopping-memory-heading" className="text-lg font-semibold">Shopping memory</h2>
            <p className="mt-2 text-sm text-zinc-300">Optional. Save explicitly stated color, material and style preferences for future shopping answers. Off until you choose to enable it.</p>
            <p className="mt-2 text-xs text-zinc-400">Preferences expire after 90 days unless stated again. No sensitive traits or personality profiles are saved by this feature. Recent chat history, orders and any older memory are separate.</p>
            <p role="status" className="mt-4 text-sm text-cyan-200">{busy ? 'Loading memory settings...' : memory ? `${error ? 'Last confirmed: shopping' : 'Shopping'} memory is ${memory.enabled ? 'on' : 'off'}. ${memory.preferences.length} saved preferences.` : 'Memory status unavailable.'}</p>
            {error && <div role="alert" className="mt-3 rounded-lg border border-red-400 p-3 text-sm text-red-200">{error}</div>}
            <div className="mt-4 flex flex-wrap gap-3">
                {memory && !memory.enabled && <button disabled={busy || !!error} onClick={() => { void changeConsent(true); }} className="rounded-lg bg-cyan-300 px-4 py-2 text-sm font-semibold text-zinc-950 disabled:opacity-40">Enable shopping memory</button>}
                {memory && <button disabled={busy || !!error} onClick={() => setConfirmDelete(true)} className="rounded-lg border border-red-300/60 px-4 py-2 text-sm text-red-200 disabled:opacity-40">Turn off and erase preferences</button>}
                {memory && <button disabled={busy || !!error} onClick={() => { void exportMemory(); }} className="rounded-lg border border-zinc-500 px-4 py-2 text-sm disabled:opacity-40">Export preferences</button>}
                <button disabled={busy} onClick={() => { void refresh(); }} className="rounded-lg border border-zinc-500 px-4 py-2 text-sm disabled:opacity-40">Refresh settings</button>
            </div>
            {confirmDelete && <div className="mt-4 rounded-lg border border-red-400/60 p-4">
                <p className="text-sm text-red-100">Turn off shopping memory and erase these saved preferences? This cannot be undone. It does not delete chat history or order records.</p>
                <div className="mt-3 flex flex-wrap gap-3">
                    <button disabled={busy || !!error} onClick={() => { void changeConsent(false); }} className="rounded-lg bg-red-200 px-3 py-2 text-sm font-semibold text-red-950 disabled:opacity-40">Confirm erase</button>
                    <button disabled={busy} onClick={() => setConfirmDelete(false)} className="rounded-lg border border-zinc-500 px-3 py-2 text-sm">Cancel</button>
                </div>
            </div>}
            {exportText && <div className="mt-4"><label htmlFor="shopping-memory-export" className="text-sm">Your preferences export (JSON)</label><textarea id="shopping-memory-export" readOnly value={exportText} rows={8} className="mt-2 w-full rounded-lg border border-zinc-500 bg-black p-3 text-xs text-zinc-200" /></div>}
        </section>
    );
}
