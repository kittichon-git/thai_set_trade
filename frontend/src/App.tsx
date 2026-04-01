// App.tsx — Root application component for DW Dashboard
import { useState, useCallback } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useBreakpoint } from './hooks/useBreakpoint';
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

type Tab = 'dashboard' | 'history' | 'dw-universe' | 'dw-all';

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

const NAV_ITEMS = [
  { id: 'dashboard',    icon: '📊', label: 'Dashboard' },
  { id: 'history',      icon: '🕐', label: 'ประวัติสัญญาณ' },
  { id: 'dw-universe',  icon: '📋', label: 'DW Universe' },
  { id: 'dw-all',       icon: '📂', label: 'DW ทั้งหมด' },
] as const;

export default function App() {
  const { payload, status, forceReconnect } = useWebSocket(WS_URL);
  const breakpoint = useBreakpoint();
  const [expandedIdx, setExpandedIdx] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleToggle = useCallback((idx: string) => {
    setExpandedIdx((prev) => (prev === idx ? null : idx));
  }, []);

  const isMobile = breakpoint === 'mobile';

  const activeSignals = payload?.signals && payload.signals.length > 0 ? payload.signals : MOCK_SIGNALS;
  const actionableTypes = ['Intraday Spike', 'Opening Vol', 'Gap Up + Vol'];
  const spikeSignals = activeSignals.filter(s => actionableTypes.includes(s.signal_type)).slice(0, 3);
  const moneyFlowSignals = activeSignals.filter(s => s.signal_type?.includes('Money Flow')).slice(0, 5);
  const mainBoardSignals = activeSignals.slice(0, 10);

  const pageTitle = NAV_ITEMS.find(n => n.id === activeTab)?.label ?? 'Dashboard';

  return (
    <div className="min-h-[100dvh] bg-[#0d1117] text-slate-100 flex">

      {/* ── Sidebar ─────────────────────────────────────────── */}
      {/* Mobile overlay */}
      {isMobile && sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/60" onClick={() => setSidebarOpen(false)} />
      )}

      <aside className={`
        fixed top-0 left-0 h-full z-50 flex flex-col
        w-56 bg-[#111827] border-r border-white/5
        transition-transform duration-200
        ${isMobile ? (sidebarOpen ? 'translate-x-0' : '-translate-x-full') : 'translate-x-0'}
      `}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 py-5">
          <div className="w-8 h-8 rounded-lg bg-emerald-500 flex items-center justify-center text-sm font-bold text-white shadow-lg shadow-emerald-500/30">T</div>
          <span className="font-bold text-white text-sm tracking-wide">Thai SET Trade</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 pb-4 overflow-y-auto">
          <div className="mb-2 px-2">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest">MARKET</span>
          </div>
          {NAV_ITEMS.map(({ id, icon, label }) => (
            <button
              key={id}
              onClick={() => { setActiveTab(id as Tab); setSidebarOpen(false); }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-all mb-0.5 ${
                activeTab === id
                  ? 'bg-emerald-500/15 text-emerald-400 font-medium shadow-sm'
                  : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
              }`}
            >
              <span className="text-base leading-none">{icon}</span>
              <span>{label}</span>
              {id === 'dw-universe' && payload?.dw_universe_count ? (
                <span className="ml-auto text-[10px] bg-slate-700/80 text-slate-400 px-1.5 py-0.5 rounded num">{payload.dw_universe_count}</span>
              ) : id === 'dw-all' && payload?.dw_all_count ? (
                <span className="ml-auto text-[10px] bg-slate-700/80 text-slate-400 px-1.5 py-0.5 rounded num">{payload.dw_all_count}</span>
              ) : null}
            </button>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-4 border-t border-white/5">
          <div className={`flex items-center gap-2 text-xs mb-1 ${
            status === 'connected' ? 'text-emerald-400' :
            status === 'connecting' ? 'text-yellow-400' : 'text-red-400'
          }`}>
            <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
              status === 'connected' ? 'bg-emerald-400 shadow-sm shadow-emerald-400' :
              status === 'connecting' ? 'bg-yellow-400 animate-pulse' : 'bg-red-400'
            }`} />
            {status === 'connected' ? 'เชื่อมต่อแล้ว' : status === 'connecting' ? 'กำลังเชื่อมต่อ...' : 'ขาดการเชื่อมต่อ'}
          </div>
          {payload && (
            <div className={`text-xs font-semibold px-2 py-1 rounded-lg inline-block mt-1 ${
              payload.market_status === 'OPEN'
                ? 'bg-emerald-500/15 text-emerald-400'
                : 'bg-slate-700/50 text-slate-400'
            }`}>{payload.market_status}</div>
          )}
        </div>
      </aside>

      {/* ── Main area ───────────────────────────────────────── */}
      <div className={`flex-1 flex flex-col min-h-[100dvh] ${isMobile ? '' : 'ml-56'}`}>

        {/* Top header */}
        <header className="sticky top-0 z-30 flex items-center gap-3 px-5 py-3.5 bg-[#0d1117]/90 backdrop-blur-md border-b border-white/5">
          {isMobile && (
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-colors"
            >
              ☰
            </button>
          )}
          {/* Breadcrumb */}
          <div className="flex items-center gap-1.5 text-sm">
            <span className="text-slate-500">Home</span>
            <span className="text-slate-700">/</span>
            <span className="text-slate-200 font-medium">{pageTitle}</span>
          </div>
          <div className="ml-auto flex items-center gap-2">
            {payload?.timestamp && (
              <span className="text-xs text-slate-500 hidden sm:block">{payload.timestamp}</span>
            )}
            {payload?.signal_count != null && (
              <span className="text-xs bg-emerald-500/15 text-emerald-400 px-2.5 py-1 rounded border border-emerald-500/20 font-medium">
                {payload.signal_count} สัญญาณ
              </span>
            )}
            {status !== 'connected' && (
              <span className={`text-xs px-2.5 py-1 rounded border font-medium ${
                status === 'connecting'
                  ? 'bg-yellow-500/15 text-yellow-400 border-yellow-500/20'
                  : 'bg-red-500/15 text-red-400 border-red-500/20'
              }`}>
                {status === 'connecting' ? 'กำลังเชื่อมต่อ...' : 'ขาดการเชื่อมต่อ'}
              </span>
            )}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4">
          {activeTab === 'dw-universe' ? (
            <DWUniversePage apiUrl={API_URL} endpoint="/dw-universe" title="DW Universe (Filtered)" />
          ) : activeTab === 'dw-all' ? (
            <DWUniversePage apiUrl={API_URL} endpoint="/dw-all" title="DW ทั้งหมด" />
          ) : activeTab === 'history' ? (
            <SignalHistory apiUrl={API_URL} />
          ) : (
            /* Dashboard */
            <>
              {activeTab === 'dashboard' && payload?.dw_universe_count === 0 && <EmptyDWBanner />}
              {!payload && activeSignals === MOCK_SIGNALS ? (
                <LoadingState />
              ) : isMobile ? (
                <PullToRefresh onRefresh={forceReconnect}>
                  {activeSignals.length === 0 ? (
                    <div className="text-center py-16 text-slate-500">
                      <div className="text-4xl mb-3">🔍</div>
                      <div className="text-base font-medium">ยังไม่พบสัญญาณ</div>
                      <div className="text-sm mt-1 text-slate-600">กำลังรอข้อมูล...</div>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-6">
                      {spikeSignals.length > 0 && (
                        <div>
                          <div className="mb-3 flex items-center gap-2">
                            <span className="text-xl">⚡</span>
                            <span className="text-slate-400 text-sm font-medium">Top Spikes</span>
                            <span className="bg-slate-800 text-slate-400 text-xs px-2 py-0.5 rounded num">{spikeSignals.length}</span>
                          </div>
                          {spikeSignals.map((sig, idx) => (
                            <StockSignalCard key={`spike-${sig.symbol}`} signal={sig} rank={idx + 1}
                              isExpanded={expandedIdx === `spike-${idx}`} onToggle={() => handleToggle(`spike-${idx}`)} apiUrl={API_URL} />
                          ))}
                        </div>
                      )}
                      {mainBoardSignals.length > 0 && (
                        <div>
                          <div className="mb-3 flex items-center gap-2">
                            <span className="text-xl">🔥</span>
                            <span className="text-slate-400 text-sm font-medium">Main Board — Top 10</span>
                            <span className="bg-slate-800 text-slate-400 text-xs px-2 py-0.5 rounded num">{mainBoardSignals.length}</span>
                          </div>
                          {mainBoardSignals.map((sig, idx) => (
                            <StockSignalCard key={`main-${sig.symbol}`} signal={sig} rank={idx + 1}
                              isExpanded={expandedIdx === `main-${idx}`} onToggle={() => handleToggle(`main-${idx}`)} apiUrl={API_URL} />
                          ))}
                        </div>
                      )}
                      {moneyFlowSignals.length > 0 && (
                        <div>
                          <div className="mb-3 flex items-center gap-2">
                            <span className="text-xl">💸</span>
                            <span className="text-slate-400 text-sm font-medium">Money Flow</span>
                            <span className="bg-slate-800 text-slate-400 text-xs px-2 py-0.5 rounded num">{moneyFlowSignals.length}</span>
                          </div>
                          {moneyFlowSignals.map((sig, idx) => (
                            <StockSignalCard key={`money-${sig.symbol}`} signal={sig} rank={idx + 1}
                              isExpanded={expandedIdx === `money-${idx}`} onToggle={() => handleToggle(`money-${idx}`)} apiUrl={API_URL} />
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </PullToRefresh>
              ) : (
                <div className="grid grid-cols-2 gap-4 items-start">
                  {/* คอลัมน์ซ้าย: Main Board */}
                  <div className="flex flex-col gap-4">
                    {mainBoardSignals.length > 0 && (
                      <StockSignalTable title="Main Board — Top 10" icon="🔥" signals={mainBoardSignals} breakpoint={breakpoint} apiUrl={API_URL} />
                    )}
                  </div>
                  {/* คอลัมน์ขวา: Spikes + Money Flow */}
                  <div className="flex flex-col gap-4">
                    {spikeSignals.length > 0 && (
                      <StockSignalTable title="Top Spikes (Actionable)" icon="⚡" signals={spikeSignals} breakpoint={breakpoint} apiUrl={API_URL} />
                    )}
                    {moneyFlowSignals.length > 0 && (
                      <StockSignalTable title="Money Flow Leaderboard" icon="💸" signals={moneyFlowSignals} breakpoint={breakpoint} apiUrl={API_URL} />
                    )}
                  </div>
                </div>
              )}

              {/* Signal history ใต้ dashboard (desktop เท่านั้น) */}
              {!isMobile && (
                <div className="mt-6 border-t border-slate-800/60 pt-6">
                  <SignalHistory apiUrl={API_URL} />
                </div>
              )}
            </>
          )}
        </main>

        <footer className="text-center text-slate-700 text-xs py-3 border-t border-white/5">
          thaiwarrant.com + MT5 | อัปเดตทุก 10 วินาที
        </footer>
      </div>
    </div>
  );
}
