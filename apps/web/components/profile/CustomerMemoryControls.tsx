'use client';

import { useEffect, useState } from 'react';
import { Brain } from 'lucide-react';
import { api } from '@/lib/api';

type MemoryExport = {
    enabled: boolean;
    retention_days: number | null;
    preferences: { category: string; value: string; created_at: string; expires_at: string }[];
};

export default function CustomerMemoryControls() {
    const [memory, setMemory] = useState<MemoryExport | null>(null);
    const [busy, setBusy] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [confirmDelete, setConfirmDelete] = useState(false);
    const [confirmAll,setConfirmAll]=useState(false);
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
            await api.put('/users/me/memory/consent', { enabled });
            await load();
            setConfirmDelete(false);
        } catch {
            setError('The memory change could not be confirmed. Refresh these settings before trying again.');
        } finally { setBusy(false); }
    };
    const erasePreferences = async () => {
        if (busy) return;
        setBusy(true);setError(null);setExportText(null);
        try { await api.delete('/users/me/memory');await load();setConfirmDelete(false); }
        catch { setError('Erasing saved preferences could not be confirmed. Refresh before retrying.'); }
        finally { setBusy(false); }
    };
    const eraseAll = async () => {
        if (busy) return;
        setBusy(true);setError(null);setExportText(null);
        try {
            const {data}=await api.delete('/users/me/memory/personalization');
            if (!data || data.deleted!==true) throw new Error('Incomplete erase');
            await load();setConfirmAll(false);
        } catch { setError('Full personalization erase is not confirmed. Learning is stopped where confirmed; some stores may still need cleanup. Refresh and retry.'); }
        finally { setBusy(false); }
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
        <section aria-labelledby="shopping-memory-heading" className="mt-10 w-full rounded-[28px] bg-[#050505]/95 sm:bg-black/75 p-6 text-left text-white shadow-[0_24px_100px_rgba(0,0,0,0.5)] backdrop-blur-2xl sm:p-8">
            <div className="flex items-start justify-between gap-4"><div><p className="mb-2 text-[10px] font-medium uppercase tracking-[0.22em] text-white/40">Personalization</p><h2 id="shopping-memory-heading" className="text-xl font-semibold tracking-tight">Shopping memory</h2></div><span aria-hidden="true" className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white/[0.06] text-white/65"><Brain size={21} /></span></div>
            <p className="mt-4 text-sm leading-6 text-zinc-300">Optional learning. Save customer-stated shopping preferences for future answers. Current requests always win. New learning is off until you choose to enable it.</p>
            <p className="mt-3 text-xs leading-6 text-zinc-400">Newly enabled memory is long-term, until you erase it. Turning learning off keeps using saved preferences but stops new learning.</p>
            <details open={!memory?.enabled} className="mt-4 rounded-2xl bg-white/[0.025] px-4 py-3 text-xs leading-[1.8] text-zinc-400"><summary className="cursor-pointer py-1 text-sm font-medium text-white/70 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white">What is saved and how it is used</summary><p className="pt-3">No sensitive traits, credentials or inferred personality labels. Recent chat and order records are separate. Enabling accepts long-term storage across 20 shopping categories: colors, materials, styles, fit, patterns, sleeves, necklines, closures, finishes, shapes, portability, durability, comfort, care, packaging, sourcing, shopping priorities, delivery preferences, and catalog-supported brands and categories. Consented shopping interactions may update bounded behavior caches. Those are shopping signals, not personality, health or wealth claims.</p></details>
            <p role="status" className="mt-6 rounded-2xl bg-white/[0.045] px-4 py-3.5 text-sm leading-6 text-white/80">{busy ? 'Loading memory settings...' : memory ? `${error ? 'Last confirmed: shopping' : 'Shopping'} learning is ${memory.enabled ? 'on' : 'off'}. ${memory.preferences.length} saved preferences.` : 'Memory status unavailable.'}</p>
            {error && <div role="alert" className="mt-3 rounded-lg border border-red-400 p-3 text-sm text-red-200">{error}</div>}
            <div className="mt-5 flex flex-wrap gap-2.5">
                {memory && !memory.enabled && <button disabled={busy || !!error} onClick={() => { void changeConsent(true); }} className="min-h-11 rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-black transition hover:bg-white/85 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white disabled:opacity-40">Enable shopping learning</button>}
                {memory && <button disabled={busy || !!error} onClick={() => { void changeConsent(false); }} className="min-h-11 rounded-full bg-white/[0.055] px-4 py-2.5 text-sm text-rose-200/90 transition hover:bg-rose-300/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white disabled:opacity-40">Turn learning off</button>}
                {memory && <button disabled={busy || !!error} onClick={() => setConfirmDelete(true)} className="min-h-11 rounded-full bg-white/[0.055] px-4 py-2.5 text-sm text-rose-200/90 transition hover:bg-rose-300/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white disabled:opacity-40">Erase saved preferences</button>}
                {memory && <button disabled={busy || !!error} onClick={() => setConfirmAll(true)} className="min-h-11 rounded-full bg-white/[0.055] px-4 py-2.5 text-sm text-rose-200/90 transition hover:bg-rose-300/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white disabled:opacity-40">Erase all personalization</button>}
                {memory && <button disabled={busy || !!error} onClick={() => { void exportMemory(); }} className="min-h-11 rounded-full bg-white/[0.055] px-4 py-2.5 text-sm text-white/75 transition hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white disabled:opacity-40">Export preferences</button>}
                <button disabled={busy} onClick={() => { void refresh(); }} className="min-h-11 rounded-full bg-white/[0.055] px-4 py-2.5 text-sm text-white/75 transition hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white disabled:opacity-40">Refresh settings</button>
            </div>
            {confirmDelete && <div className="mt-4 rounded-lg border border-red-400/60 p-4">
                <p className="text-sm text-red-100">Stop learning and erase these saved preferences? This cannot be undone. It does not delete chat history or order records.</p>
                <div className="mt-3 flex flex-wrap gap-3">
                    <button disabled={busy || !!error} onClick={() => { void erasePreferences(); }} className="rounded-lg bg-red-200 px-3 py-2 text-sm font-semibold text-red-950 disabled:opacity-40">Confirm erase</button>
                    <button disabled={busy} onClick={() => setConfirmDelete(false)} className="rounded-lg border border-zinc-500 px-3 py-2 text-sm">Cancel</button>
                </div>
            </div>}
            {confirmAll && <div className="mt-4 rounded-lg border border-red-400/60 p-4">
                <p className="text-sm text-red-100">Stop learning and erase all saved preferences, shopping behavior, derived profiles, recent personalized chat context and shown-product history? Account, cart and orders stay unchanged. This cannot be undone. Cleanup must be confirmed across all stores.</p>
                <div className="mt-3 flex flex-wrap gap-3">
                    <button disabled={busy || !!error} onClick={() => { void eraseAll(); }} className="rounded-lg bg-red-200 px-3 py-2 text-sm font-semibold text-red-950 disabled:opacity-40">Confirm erase all</button>
                    <button disabled={busy} onClick={() => setConfirmAll(false)} className="rounded-lg border border-zinc-500 px-3 py-2 text-sm">Keep personalization</button>
                </div>
            </div>}
            {exportText && <div className="mt-4"><label htmlFor="shopping-memory-export" className="text-sm">Your preferences export (JSON)</label><textarea id="shopping-memory-export" readOnly value={exportText} rows={8} className="mt-2 w-full rounded-lg border border-zinc-500 bg-black p-3 text-xs text-zinc-200" /></div>}
        </section>
    );
}
