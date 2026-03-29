// App.tsx — Root application component for DW Dashboard
import { useState, useCallback } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useBreakpoint } from './hooks/useBreakpoint';
import ConnectionBanner from './components/ConnectionBanner';
import StatusBar from './components/StatusBar';
import EmptyDWBanner from './components/EmptyDWBanner';
import LoadingState from './components/LoadingState';
import StockSignalTable from './components/StockSignalTable';
import StockSignalCard from './components/StockSignalCard';
import SignalHistory from './components/SignalHistory';
import PullToRefresh from './components/PullToRefresh';
import DWUniversePage from './components/DWUniversePage';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/dashboard';
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type Tab = 'dashboard' | 'dw-universe' | 'dw-all';

export default function App() {
  const { payload, status, lastUpdate, forceReconnect } = useWebSocket(WS_URL);
  const breakpoint = useBreakpoint();
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');

  const handleToggle = useCallback((idx: number) => {
    setExpandedIdx((prev) => (prev === idx ? null : idx));
  }, []);

  const isMobile = breakpoint === 'mobile';

  return (
    <div className="min-h-[100dvh] bg-slate-950 text-slate-100">
      {/* Connection status banner — shown only when not connected */}
      <ConnectionBanner status={status} />

      {/* Sticky status bar */}
      <StatusBar payload={payload} status={status} lastUpdate={lastUpdate} />

      {/* Tab navigation */}
      <div className="sticky top-[var(--statusbar-height,3rem)] z-30 bg-slate-950 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-6">
          <div className="flex gap-1 pt-2 pb-0">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`px-4 py-2 text-sm font-medium rounded-t transition-colors border-b-2 ${
                activeTab === 'dashboard'
                  ? 'border-blue-500 text-blue-400 bg-slate-900'
                  : 'border-transparent text-slate-500 hover:text-slate-300 hover:bg-slate-900/50'
              }`}
            >
              📊 Dashboard
            </button>
            <button
              onClick={() => setActiveTab('dw-universe')}
              className={`px-4 py-2 text-sm font-medium rounded-t transition-colors border-b-2 flex items-center gap-1.5 ${
                activeTab === 'dw-universe'
                  ? 'border-blue-500 text-blue-400 bg-slate-900'
                  : 'border-transparent text-slate-500 hover:text-slate-300 hover:bg-slate-900/50'
              }`}
            >
              📋 DW Universe
              {payload && payload.dw_universe_count > 0 && (
                <span className="text-xs bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded-full num">
                  {payload.dw_universe_count}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('dw-all')}
              className={`px-4 py-2 text-sm font-medium rounded-t transition-colors border-b-2 flex items-center gap-1.5 ${
                activeTab === 'dw-all'
                  ? 'border-blue-500 text-blue-400 bg-slate-900'
                  : 'border-transparent text-slate-500 hover:text-slate-300 hover:bg-slate-900/50'
              }`}
            >
              📋 dw ทั้งหมด
            </button>
          </div>
        </div>
      </div>

      {/* DW universe empty warning (dashboard tab only) */}
      {activeTab === 'dashboard' && payload?.dw_universe_count === 0 && <EmptyDWBanner />}

      {/* Tab content */}
      {activeTab === 'dw-universe' ? (
        <DWUniversePage apiUrl={API_URL} endpoint="/dw-universe" title="DW Universe (Filtered)" />
      ) : activeTab === 'dw-all' ? (
        <DWUniversePage apiUrl={API_URL} endpoint="/dw-all" title="dw ทั้งหมด (All Scraped)" />
      ) : (
        /* Dashboard tab */
        <main className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-6 py-4">
          {!payload ? (
            <LoadingState />
          ) : isMobile ? (
            /* Mobile: Pull-to-refresh cards */
            <PullToRefresh onRefresh={forceReconnect}>
              <div className="mb-3 flex items-center gap-2">
                <span className="text-slate-400 text-sm font-medium">🔥 Volume Anomaly — Top 10</span>
                {payload.signals.length > 0 && (
                  <span className="bg-slate-800 text-slate-400 text-xs px-2 py-0.5 rounded-full num">
                    {payload.signals.length}
                  </span>
                )}
              </div>

              {payload.signals.length === 0 ? (
                <div className="fade-in text-center py-16 text-slate-500">
                  <div className="text-4xl mb-3">🔍</div>
                  <div className="text-base font-medium">ยังไม่พบสัญญาณ</div>
                  <div className="text-sm mt-1 text-slate-600">กำลังรอข้อมูล...</div>
                </div>
              ) : (
                <div>
                  {payload.signals.map((sig, idx) => (
                    <StockSignalCard
                      key={sig.symbol}
                      signal={sig}
                      rank={idx + 1}
                      isExpanded={expandedIdx === idx}
                      onToggle={() => handleToggle(idx)}
                    />
                  ))}
                </div>
              )}
            </PullToRefresh>
          ) : (
            /* Desktop/Tablet: Data table */
            <StockSignalTable
              signals={payload.signals}
              breakpoint={breakpoint}
            />
          )}

          {/* Signal history section */}
          <div className="mt-6 border-t border-slate-800/60 pt-6">
            <SignalHistory apiUrl={API_URL} />
          </div>
        </main>
      )}

      {/* Footer */}
      <footer className="text-center text-slate-600 text-xs py-4 pb-[calc(1rem+env(safe-area-inset-bottom))]">
        ข้อมูล: thaiwarrant.com + Yahoo Finance (.BK) | Phase 1 | อัปเดตทุก 10 วินาที
      </footer>
    </div>
  );
}
