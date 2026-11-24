import React from 'react';

/** Shared visual badge used by the catalog and home shopping hero. */
export function AISecuredOrdersBadge() {
  return (
    <div className="inline-flex items-center gap-2 px-3 sm:px-4 py-1.5 sm:py-2 rounded-full bg-[#0D0D0C]/80 border border-white/10 backdrop-blur-xl mb-6 sm:mb-8 shadow-2xl relative z-10">
      <span className="w-1.5 sm:w-2 h-1.5 sm:h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_10px_rgba(34,211,238,0.8)]" />
      <span className="text-[8px] sm:text-[10px] font-mono text-gray-300 uppercase tracking-[0.2em]">AI-SECURED ORDERS</span>
    </div>
  );
}
