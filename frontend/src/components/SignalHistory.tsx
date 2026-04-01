// SignalHistory.tsx — Grouped signal history: 1 record per stock per day
import { memo, useState, useEffect, useCallback } from 'react';
import type { SignalRecord, SignalHistoryResponse } from '../types';
import { formatVolume, formatChangePct, formatThaiDate } from '../utils/format';
import VolumeRatioBadge from './VolumeRatioBadge';

interface Props {
  apiUrl: string;
}

const REFRESH_INTERVAL_MS = 60_000;

const SignalHistory = memo(({ apiUrl }: Props) => {
  const [records, setRecords] = useState<SignalRecord[]>([]);
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchHistory = useCallback(
    async (date?: string) => {
      setIsLoading(true);
      setError(null);
      try {
        const url = date
          ? `${apiUrl}/signals/history?date=${date}`
          : `${apiUrl}/signals/history`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: SignalHistoryResponse = await res.json();
        setRecords(data.records);
        setAvailableDates(data.available_dates);
        if (!date && data.date) setSelectedDate(data.date);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'โหลดข้อมูลไม่สำเร็จ');
      } finally {
        setIsLoading(false);
      }
    },
    [apiUrl]
  );

  useEffect(() => {
    fetchHistory();
    const interval = setInterval(() => fetchHistory(selectedDate || undefined), REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchHistory, selectedDate]);

  const handleDateChange = (date: string) => {
    setSelectedDate(date);
    fetchHistory(date);
  };

  const marketWideCount = records.filter((r) => r.is_market_wide).length;

  return (
    <section className="mt-2">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
        <button
          className="flex items-center gap-2 text-slate-300 hover:text-slate-100 transition-colors"
          onClick={() => setIsCollapsed((v) => !v)}
        >
          <span className="font-semibold text-sm">📊 ประวัติสัญญาณวันนี้</span>
          {records.length > 0 && (
            <span className="bg-emerald-900/60 text-emerald-300 text-xs px-2 py-0.5 rounded-full num border border-emerald-800/50">
              {records.length} หุ้น
            </span>
          )}
          {marketWideCount > 0 && (
            <span className="bg-amber-900/60 text-amber-300 text-xs px-2 py-0.5 rounded-full border border-amber-800/50">
              ⚠ ตลาดร้อน
            </span>
          )}
          <span className={`text-slate-500 text-xs transition-transform duration-200 ${isCollapsed ? '' : 'rotate-180'}`}>▾</span>
        </button>

        <div className="flex items-center gap-2">
          {availableDates.length > 0 && (
            <select
              value={selectedDate}
              onChange={(e) => handleDateChange(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-300 text-xs rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-slate-500 cursor-pointer"
            >
              {availableDates.map((d) => (
                <option key={d} value={d}>{formatThaiDate(d)} ({d})</option>
              ))}
            </select>
          )}
          <button
            onClick={() => fetchHistory(selectedDate || undefined)}
            disabled={isLoading}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors disabled:opacity-50"
          >
            <span className={`text-sm ${isLoading ? 'animate-spin' : ''}`}>↻</span>
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <div className="fade-in space-y-1.5">
          {error && (
            <div className="text-red-400 text-sm bg-red-900/20 border border-red-800/50 rounded-lg px-4 py-2.5">
              โหลดข้อมูลไม่สำเร็จ: {error}
            </div>
          )}

          {isLoading && records.length === 0 && (
            <div className="text-slate-500 text-sm text-center py-8 animate-pulse">
              กำลังโหลดประวัติสัญญาณ...
            </div>
          )}

          {!isLoading && records.length === 0 && !error && (
            <div className="text-slate-600 text-sm text-center py-8 bg-slate-800/30 rounded-xl border border-slate-800/50">
              ยังไม่มีสัญญาณในวันที่เลือก
            </div>
          )}

          {records.map((rec) => {
            const isExpanded = expandedId === rec.id;
            return (
              <div
                key={rec.id}
                className={`rounded-xl border overflow-hidden transition-colors ${
                  rec.is_market_wide
                    ? 'border-amber-800/40 bg-amber-950/20'
                    : 'border-slate-800/60 bg-slate-900/30'
                }`}
              >
                {/* Main row */}
                <button
                  className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-slate-800/30 transition-colors text-left"
                  onClick={() => setExpandedId(isExpanded ? null : rec.id)}
                >
                  {/* Symbol + time range */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-slate-100 text-sm">{rec.symbol}</span>

                      {/* Market wide warning */}
                      {rec.is_market_wide && (
                        <span className="text-xs bg-amber-900/50 text-amber-400 px-1.5 py-0.5 rounded border border-amber-800/40">
                          ⚠ ตลาดร้อน {rec.simultaneous_count + 1} ตัว
                        </span>
                      )}

                      {/* Time range */}
                      <span className="text-slate-500 text-xs num font-mono">
                        {rec.first_seen}
                        {rec.first_seen !== rec.last_seen && (
                          <span> → {rec.last_seen}</span>
                        )}
                      </span>

                      {/* Pulse count */}
                      {rec.pulses.length > 1 && (
                        <span className="text-xs bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded-full num">
                          {rec.pulses.length} ครั้ง
                        </span>
                      )}
                    </div>

                    {/* Price + volume */}
                    <div className="flex items-center gap-2 mt-0.5 text-xs num text-slate-400">
                      <span>฿{rec.last_price.toFixed(2)}</span>
                      <span className={rec.change_pct > 0 ? 'text-emerald-400' : rec.change_pct < 0 ? 'text-red-400' : ''}>
                        {formatChangePct(rec.change_pct)}
                      </span>
                      <span className="text-slate-600">·</span>
                      <span>Vol {formatVolume(rec.today_volume)}</span>
                      <span className="text-slate-600">·</span>
                      <span>DW {rec.dw_count}</span>
                    </div>
                  </div>

                  {/* Max ratio badge */}
                  <VolumeRatioBadge ratio={rec.max_ratio} strength={rec.strength} />

                  {/* Expand indicator */}
                  <span className={`text-slate-600 text-xs ml-1 transition-transform ${isExpanded ? 'rotate-180' : ''}`}>▼</span>
                </button>

                {/* Pulse timeline (expanded) */}
                {isExpanded && (
                  <div className="border-t border-slate-800/50 px-3 py-2 bg-slate-950/30">
                    <div className="text-xs text-slate-500 mb-2 font-medium">Timeline สัญญาณ</div>
                    <div className="space-y-1.5">
                      {rec.pulses.map((pulse, i) => (
                        <div key={i} className="flex flex-col gap-1 pb-2 border-b border-slate-800/30 last:border-0">
                          <div className="flex items-center gap-3">
                            {/* Timeline dot */}
                            <div className="flex flex-col items-center w-4">
                              <div className={`w-2 h-2 rounded-full ${
                                pulse.ratio >= 5.0 ? 'bg-red-500' :
                                pulse.ratio >= 3.0 ? 'bg-orange-500' : 'bg-yellow-500'
                              }`} />
                            </div>
                            <span className="text-slate-500 num font-mono text-xs w-16">{pulse.time}</span>
                            <span className="text-[10px] bg-slate-800 text-blue-300 px-1.5 py-0.5 rounded border border-slate-700/40 uppercase font-bold tracking-wider">
                              {pulse.signal_type || 'Volume'}
                            </span>
                            <VolumeRatioBadge ratio={pulse.ratio} strength={pulse.strength} />
                          </div>
                          {/* DW bid/ask ณ เวลาสัญญาณ */}
                          {pulse.top_dw_code && (
                            <div className="ml-7 flex items-center gap-2 flex-wrap">
                              <span className="text-xs font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/30">
                                {pulse.top_dw_code}
                              </span>
                              {pulse.top_dw_volume != null && (
                                <span className="text-xs text-slate-500">
                                  Vol {pulse.top_dw_volume.toLocaleString()}
                                </span>
                              )}
                              {pulse.top_dw_bid != null && pulse.top_dw_bid > 0 && (
                                <span className="text-xs text-slate-400">
                                  Bid <span className="text-red-400 num">{pulse.top_dw_bid.toFixed(2)}</span>
                                </span>
                              )}
                              {pulse.top_dw_ask != null && pulse.top_dw_ask > 0 && (
                                <span className="text-xs text-slate-400">
                                  Ask <span className="text-emerald-400 num">{pulse.top_dw_ask.toFixed(2)}</span>
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>

                    {/* DW codes */}
                    {rec.dw_codes.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-slate-800/40">
                        <div className="text-xs text-slate-600 mb-1">DW</div>
                        <div className="flex flex-wrap gap-1">
                          {rec.dw_codes.slice(0, 6).map((code) => (
                            <span key={code} className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono">
                              {code}
                            </span>
                          ))}
                          {rec.dw_codes.length > 6 && (
                            <span className="text-xs text-slate-600">+{rec.dw_codes.length - 6}</span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
});

SignalHistory.displayName = 'SignalHistory';
export default SignalHistory;
