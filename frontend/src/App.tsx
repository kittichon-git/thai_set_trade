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
import type { StockSignal } from './types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/dashboard';
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type Tab = 'dashboard' | 'dw-universe' | 'dw-all';

const MOCK_SIGNALS: StockSignal[] = [
  {
    symbol: "DELTA",
    last_price: 112.50,
    change_pct: 4.5,
    today_volume: 15400000,
    avg_5d_volume: 3200000,
    volume_ratio: 4.8,
    strength: "High",
    signal_type: "Intraday Spike",
    signal_value: 4.8,
    dw_list: [{ dw_code: "DELTA01C2405A", dw_type: "Call", issuer: "01", dw_price: 0.45, underlying: "DELTA", gearing: 5.2, moneyness: "OTM", expiry_date: "2024-05-15", days_remaining: 45, dw_volume: 1200000 }],
    updated_at: new Date().toISOString(),
    sparkline: [105, 107, 106, 110, 112.5],
    ohlc: [
      { time: "2024-03-25", open: 103, high: 108, low: 102, close: 105, volume: 8000000 },
      { time: "2024-03-26", open: 105, high: 109, low: 104, close: 107, volume: 9200000 },
      { time: "2024-03-27", open: 107, high: 108, low: 104, close: 106, volume: 7500000 },
      { time: "2024-03-28", open: 106, high: 112, low: 105, close: 110, volume: 11000000 },
      { time: "2024-03-29", open: 110, high: 114, low: 109, close: 112.5, volume: 15400000 },
    ],
  },
  {
    symbol: "KBANK",
    last_price: 125.00,
    change_pct: 2.1,
    today_volume: 8500000,
    avg_5d_volume: 4000000,
    volume_ratio: 2.1,
    strength: "Normal",
    signal_type: "Opening Vol",
    signal_value: 2.1,
    dw_list: [{ dw_code: "KBANK13C2406A", dw_type: "Call", issuer: "13", dw_price: 0.32, underlying: "KBANK", gearing: 6.1, moneyness: "ATM", expiry_date: "2024-06-10", days_remaining: 70, dw_volume: 500000 }],
    updated_at: new Date().toISOString(),
    sparkline: [120, 121, 122, 122.5, 125],
    ohlc: [
      { time: "2024-03-25", open: 119, high: 121, low: 118, close: 120, volume: 3000000 },
      { time: "2024-03-26", open: 120, high: 122, low: 119, close: 121, volume: 3500000 },
      { time: "2024-03-27", open: 121, high: 123, low: 120, close: 122, volume: 3200000 },
      { time: "2024-03-28", open: 122, high: 123, low: 121, close: 122.5, volume: 2800000 },
      { time: "2024-03-29", open: 122.5, high: 126, low: 122, close: 125, volume: 8500000 },
    ],
  },
  {
    symbol: "AOT",
    last_price: 65.25,
    change_pct: 1.5,
    today_volume: 22000000,
    avg_5d_volume: 15000000,
    volume_ratio: 1.4,
    strength: "Normal",
    signal_type: "Gap Up + Vol",
    signal_value: 1.5,
    dw_list: [],
    updated_at: new Date().toISOString(),
    sparkline: [63, 63.5, 64, 64.25, 65.25],
    ohlc: [
      { time: "2024-03-25", open: 62.5, high: 63.5, low: 62, close: 63, volume: 12000000 },
      { time: "2024-03-26", open: 63, high: 64, low: 62.5, close: 63.5, volume: 14000000 },
      { time: "2024-03-27", open: 63.5, high: 64.5, low: 63, close: 64, volume: 13500000 },
      { time: "2024-03-28", open: 64, high: 64.5, low: 63.5, close: 64.25, volume: 11000000 },
      { time: "2024-03-29", open: 65, high: 65.75, low: 64.5, close: 65.25, volume: 22000000 },
    ],
  },
  {
    symbol: "PTTEP",
    last_price: 162.50,
    change_pct: 0.5,
    today_volume: 5500000,
    avg_5d_volume: 5000000,
    volume_ratio: 1.1,
    strength: "Normal",
    signal_type: "Money Flow #1",
    signal_value: 3.5,
    dw_list: [{ dw_code: "PTTEP01C2407A", dw_type: "Call", issuer: "01", dw_price: 0.55, underlying: "PTTEP", gearing: 4.8, moneyness: "ITM", expiry_date: "2024-07-20", days_remaining: 110, dw_volume: 2500000 }],
    updated_at: new Date().toISOString(),
    sparkline: [160, 161, 159, 161.5, 162.5],
    ohlc: [
      { time: "2024-03-25", open: 159, high: 161, low: 158, close: 160, volume: 4000000 },
      { time: "2024-03-26", open: 160, high: 162, low: 159, close: 161, volume: 4500000 },
      { time: "2024-03-27", open: 161, high: 162, low: 158, close: 159, volume: 3800000 },
      { time: "2024-03-28", open: 159, high: 162.5, low: 158.5, close: 161.5, volume: 5200000 },
      { time: "2024-03-29", open: 161.5, high: 163, low: 161, close: 162.5, volume: 5500000 },
    ],
  },
  {
    symbol: "CPALL",
    last_price: 57.50,
    change_pct: -0.5,
    today_volume: 18000000,
    avg_5d_volume: 20000000,
    volume_ratio: 0.9,
    strength: "Normal",
    signal_type: "Money Flow #2",
    signal_value: 2.8,
    dw_list: [],
    updated_at: new Date().toISOString(),
    sparkline: [58, 57.75, 58.25, 58, 57.5],
    ohlc: [
      { time: "2024-03-25", open: 58.5, high: 59, low: 57.5, close: 58, volume: 18000000 },
      { time: "2024-03-26", open: 58, high: 58.5, low: 57.25, close: 57.75, volume: 17500000 },
      { time: "2024-03-27", open: 57.75, high: 58.75, low: 57.5, close: 58.25, volume: 19000000 },
      { time: "2024-03-28", open: 58.25, high: 58.5, low: 57.5, close: 58, volume: 16000000 },
      { time: "2024-03-29", open: 58, high: 58.25, low: 57, close: 57.5, volume: 18000000 },
    ],
  }
];

export default function App() {
  const { payload, status, lastUpdate, forceReconnect } = useWebSocket(WS_URL);
  const breakpoint = useBreakpoint();
  const [expandedIdx, setExpandedIdx] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');

  const handleToggle = useCallback((idx: string) => {
    setExpandedIdx((prev) => (prev === idx ? null : idx));
  }, []);

  const isMobile = breakpoint === 'mobile';

  // Smart Sections Categorization
  // Use MOCK_SIGNALS if it's outside market hours or no data yet for UI demonstration
  const activeSignals = payload?.signals && payload.signals.length > 0 ? payload.signals : MOCK_SIGNALS;
  
  const actionableTypes = ['Intraday Spike', 'Opening Vol', 'Gap Up + Vol'];
  const spikeSignals = activeSignals.filter(s => actionableTypes.includes(s.signal_type)).slice(0, 3);
  const moneyFlowSignals = activeSignals.filter(s => s.signal_type?.includes('Money Flow')).slice(0, 5);
  const mainBoardSignals = activeSignals.slice(0, 10);

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
              {payload && payload.dw_all_count > 0 && (
                <span className="text-xs bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded-full num">
                  {payload.dw_all_count}
                </span>
              )}
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
          {!payload && activeSignals === MOCK_SIGNALS ? (
            <LoadingState />
          ) : isMobile ? (
            /* Mobile: Pull-to-refresh cards */
            <PullToRefresh onRefresh={forceReconnect}>
              {activeSignals.length === 0 ? (
                <div className="fade-in text-center py-16 text-slate-500">
                  <div className="text-4xl mb-3">🔍</div>
                  <div className="text-base font-medium">ยังไม่พบสัญญาณ</div>
                  <div className="text-sm mt-1 text-slate-600">กำลังรอข้อมูล...</div>
                </div>
              ) : (
                <div className="flex flex-col gap-6">
                  {/* SPIKES SECTION */}
                  {spikeSignals.length > 0 && (
                    <div>
                      <div className="mb-3 flex items-center gap-2">
                        <span className="text-xl">⚡</span>
                        <span className="text-slate-400 text-sm font-medium">Top Spikes (Actionable)</span>
                        <span className="bg-slate-800 text-slate-400 text-xs px-2 py-0.5 rounded-full num">{spikeSignals.length}</span>
                      </div>
                      {spikeSignals.map((sig, idx) => (
                        <StockSignalCard
                          key={`spike-${sig.symbol}`}
                          signal={sig}
                          rank={idx + 1}
                          isExpanded={expandedIdx === `spike-${idx}`}
                          onToggle={() => handleToggle(`spike-${idx}`)}
                        />
                      ))}
                    </div>
                  )}

                  {/* MAIN BOARD SECTION */}
                  {mainBoardSignals.length > 0 && (
                    <div>
                      <div className="mb-3 flex items-center gap-2">
                        <span className="text-xl">🔥</span>
                        <span className="text-slate-400 text-sm font-medium">Main Board — Top 10</span>
                        <span className="bg-slate-800 text-slate-400 text-xs px-2 py-0.5 rounded-full num">{mainBoardSignals.length}</span>
                      </div>
                      {mainBoardSignals.map((sig, idx) => (
                        <StockSignalCard
                          key={`main-${sig.symbol}`}
                          signal={sig}
                          rank={idx + 1}
                          isExpanded={expandedIdx === `main-${idx}`}
                          onToggle={() => handleToggle(`main-${idx}`)}
                        />
                      ))}
                    </div>
                  )}

                  {/* MONEY FLOW SECTION */}
                  {moneyFlowSignals.length > 0 && (
                    <div>
                      <div className="mb-3 flex items-center gap-2">
                        <span className="text-xl">💸</span>
                        <span className="text-slate-400 text-sm font-medium">Money Flow Leaderboard</span>
                        <span className="bg-slate-800 text-slate-400 text-xs px-2 py-0.5 rounded-full num">{moneyFlowSignals.length}</span>
                      </div>
                      {moneyFlowSignals.map((sig, idx) => (
                        <StockSignalCard
                          key={`money-${sig.symbol}`}
                          signal={sig}
                          rank={idx + 1}
                          isExpanded={expandedIdx === `money-${idx}`}
                          onToggle={() => handleToggle(`money-${idx}`)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </PullToRefresh>
          ) : (
            /* Desktop/Tablet: Data tables */
            <div className="flex flex-col gap-4">
              {spikeSignals.length > 0 && (
                <StockSignalTable
                  title="Top Spikes (Actionable)"
                  icon="⚡"
                  signals={spikeSignals}
                  breakpoint={breakpoint}
                />
              )}
              {mainBoardSignals.length > 0 && (
                <StockSignalTable
                  title="Main Board — Top 10"
                  icon="🔥"
                  signals={mainBoardSignals}
                  breakpoint={breakpoint}
                />
              )}
              {moneyFlowSignals.length > 0 && (
                <StockSignalTable
                  title="Money Flow Leaderboard"
                  icon="💸"
                  signals={moneyFlowSignals}
                  breakpoint={breakpoint}
                />
              )}
            </div>
          )}

          {/* Signal history section */}
          <div className="mt-6 border-t border-slate-800/60 pt-6">
            <SignalHistory apiUrl={API_URL} />
          </div>
        </main>
      )}

      {/* Footer */}
      <footer className="text-center text-slate-600 text-xs py-4 pb-[calc(1rem+env(safe-area-inset-bottom))]">
        ข้อมูล: thaiwarrant.com + Yahoo Finance (.BK) | Phase 2 | {payload?.signals.length === 0 ? 'กำลังแสดงข้อมูลจำลอง (Mocks)' : 'อัปเดตทุก 10 วินาที'}
      </footer>
    </div>
  );
}
