// StatusBar.tsx — Sticky top status bar with market info
import { memo } from 'react';
import type { DashboardPayload } from '../types';
import MarketStatusBadge from './MarketStatusBadge';

interface Props {
  payload: DashboardPayload | null;
  status: string;
  lastUpdate: string | null;
}

const StatusBar = memo(({ payload, status, lastUpdate }: Props) => {
  const isConnected = status === 'connected';
  const marketStatus = payload?.market_status ?? 'CLOSED';
  const dwCount = payload?.dw_universe_count ?? 0;
  const signalCount = payload?.signal_count ?? 0;

  return (
    <header className="sticky top-0 z-40 w-full backdrop-blur-sm bg-slate-900/95 border-b border-slate-800/60">
      {/* Desktop layout */}
      <div className="hidden md:flex items-center justify-between max-w-7xl mx-auto px-4 lg:px-6 py-2.5 gap-4">
        {/* Left: Live indicator + Title */}
        <div className="flex items-center gap-3 min-w-0">
          <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 flex-shrink-0">
            <span
              className={`inline-block w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 live-dot' : 'bg-slate-500'}`}
            />
            {isConnected ? 'LIVE' : '—'}
          </span>
          <span className="font-bold text-slate-100 text-base tracking-tight">
            DW Dashboard
          </span>
        </div>

        {/* Center divider */}
        <div className="hidden lg:block flex-1 h-px bg-slate-800" />

        {/* Right: Market info */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <MarketStatusBadge status={marketStatus} />
          <span className="text-xs text-slate-400 num">
            DW: <span className="text-slate-200 font-semibold">{dwCount}</span>
          </span>
          <span className="text-slate-700">|</span>
          <span className="text-xs text-slate-400 num">
            สัญญาณ: <span className="text-slate-200 font-semibold">{signalCount}</span>
          </span>
          {lastUpdate && (
            <>
              <span className="text-slate-700">|</span>
              <span className="text-xs text-slate-500 num">{lastUpdate}</span>
            </>
          )}
        </div>
      </div>

      {/* Mobile layout (2 rows) */}
      <div className="md:hidden px-3 py-2">
        {/* Row 1: Live + Title + Market Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
              <span
                className={`inline-block w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 live-dot' : 'bg-slate-500'}`}
              />
              {isConnected ? 'LIVE' : '—'}
            </span>
            <span className="font-bold text-slate-100 text-sm">DW Dashboard</span>
          </div>
          <MarketStatusBadge status={marketStatus} />
        </div>

        {/* Row 2: Stats + time */}
        <div className="flex items-center gap-1.5 mt-1 text-xs text-slate-400 num">
          <span>
            DW: <span className="text-slate-300 font-medium">{dwCount}</span>
          </span>
          <span className="text-slate-700">·</span>
          <span>
            สัญญาณ: <span className="text-slate-300 font-medium">{signalCount}</span>
          </span>
          {lastUpdate && (
            <>
              <span className="text-slate-700">·</span>
              <span className="text-slate-500">{lastUpdate}</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
});

StatusBar.displayName = 'StatusBar';
export default StatusBar;
