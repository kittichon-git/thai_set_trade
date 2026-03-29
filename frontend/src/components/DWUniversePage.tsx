// DWUniversePage.tsx — Browse all DW items fetched from thaiwarrant.com
import { useState, useEffect, useMemo } from 'react';
import type { DWItem, DWUniverseResponse } from '../types';

interface Props {
  apiUrl: string;
  endpoint?: string;
  title?: string;
}

type TypeFilter = 'All' | 'Call' | 'Put';

export default function DWUniversePage({ apiUrl, endpoint = '/dw-universe', title = 'DW Universe' }: Props) {
  const [data, setData] = useState<DWUniverseResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('All');
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`${apiUrl}${endpoint}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<DWUniverseResponse>;
      })
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => { setError(String(e)); setLoading(false); });
  }, [apiUrl, endpoint]);

  const THAI_SYMBOL = /^[A-Z]+$/;

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = search.trim().toUpperCase();
    return Object.entries(data.data)
      .filter(([sym]) => THAI_SYMBOL.test(sym))
      .map(([sym, dws]) => {
        let items = dws;
        if (typeFilter !== 'All') {
          items = items.filter((d) => d.dw_type === typeFilter);
        }
        if (q) {
          if (!sym.includes(q) && !items.some((d) => d.dw_code.includes(q) || d.issuer.toUpperCase().includes(q))) {
            return null;
          }
          if (!sym.includes(q)) {
            items = items.filter((d) => d.dw_code.includes(q) || d.issuer.toUpperCase().includes(q));
          }
        }
        if (items.length === 0) return null;
        return { sym, items };
      })
      .filter(Boolean)
      .sort((a, b) => a!.sym.localeCompare(b!.sym)) as { sym: string; items: DWItem[] }[];
  }, [data, search, typeFilter, endpoint]);

  const totalDW = filtered.reduce((s, r) => s + r.items.length, 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-slate-400">
        <div className="text-center">
          <div className="animate-spin text-3xl mb-3">⟳</div>
          <div>กำลังโหลด DW Universe...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16 text-red-400">
        <div className="text-3xl mb-2">⚠</div>
        <div>โหลดข้อมูลไม่สำเร็จ: {error}</div>
        <button
          className="mt-4 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded text-sm text-slate-200"
          onClick={() => window.location.reload()}
        >
          ลองใหม่
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-6 py-4">
      {/* Header */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-200">
            {endpoint === '/dw-all' ? '📋 dw ทั้งหมด (ทุกรุ่น)' : `📋 ${title}`}
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {filtered.length} หุ้นอ้างอิง · {totalDW} DW{' '}
            {data && (
              <span className="text-slate-600">
                (ทั้งหมด {data.underlying_count} หุ้น · {data.total_dw_count} DW)
              </span>
            )}
            {endpoint === '/dw-all' && (
              <span className="ml-2 py-0.5 px-1.5 bg-slate-800 text-amber-500 rounded text-[10px] uppercase font-bold tracking-wider">
                Raw Data
              </span>
            )}
          </p>
        </div>

        {/* Search */}
        <input
          type="text"
          placeholder="ค้นหาหุ้น / DW code / issuer..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 min-w-[180px] max-w-xs bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-slate-500"
        />

        {/* Type filter */}
        <div className="flex gap-1">
          {(['All', 'Call', 'Put'] as TypeFilter[]).map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                typeFilter === t
                  ? t === 'Call'
                    ? 'bg-emerald-700 text-emerald-100'
                    : t === 'Put'
                    ? 'bg-rose-700 text-rose-100'
                    : 'bg-slate-600 text-slate-100'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-16 text-slate-500">
          <div className="text-3xl mb-2">🔍</div>
          <div>ไม่พบ DW ที่ตรงกับเงื่อนไข</div>
        </div>
      ) : (
        <div className="space-y-1">
          {filtered.map(({ sym, items }) => {
            const isExpanded = expandedSymbol === sym;
            const callCount = items.filter((d) => d.dw_type === 'Call').length;
            const putCount = items.filter((d) => d.dw_type === 'Put').length;
            return (
              <div key={sym} className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
                {/* Row header */}
                <button
                  className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-800/60 transition-colors text-left"
                  onClick={() => setExpandedSymbol(isExpanded ? null : sym)}
                >
                  <span className="font-semibold text-slate-100 w-20 shrink-0 num">{sym}</span>
                  <span className="text-slate-500 text-xs">
                    {items.length} DW
                  </span>
                  {callCount > 0 && (
                    <span className="text-xs bg-emerald-900/50 text-emerald-400 px-1.5 py-0.5 rounded">
                      C {callCount}
                    </span>
                  )}
                  {putCount > 0 && (
                    <span className="text-xs bg-rose-900/50 text-rose-400 px-1.5 py-0.5 rounded">
                      P {putCount}
                    </span>
                  )}
                  <span className="ml-auto text-slate-600 text-sm">{isExpanded ? '▲' : '▼'}</span>
                </button>

                {/* Expanded DW list */}
                {isExpanded && (
                  <div className="border-t border-slate-800 overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-slate-500 border-b border-slate-800">
                          <th className="text-left px-4 py-2 font-medium">DW Code</th>
                          <th className="text-center px-3 py-2 font-medium">Type</th>
                          <th className="text-left px-3 py-2 font-medium">Issuer</th>
                          <th className="text-right px-3 py-2 font-medium">Price</th>
                          <th className="text-right px-3 py-2 font-medium">Volume ↓</th>
                          <th className="text-right px-3 py-2 font-medium">Gearing</th>
                          <th className="text-center px-3 py-2 font-medium">Moneyness</th>
                          <th className="text-right px-3 py-2 font-medium">Expiry</th>
                          <th className="text-right px-4 py-2 font-medium">Days</th>
                        </tr>
                      </thead>
                      <tbody>
                        {items.map((dw) => (
                          <tr key={dw.dw_code} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                            <td className="px-4 py-2 font-mono text-slate-200">{dw.dw_code}</td>
                            <td className="px-3 py-2 text-center">
                              <span
                                className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                                  dw.dw_type === 'Call'
                                    ? 'bg-emerald-900/60 text-emerald-400'
                                    : 'bg-rose-900/60 text-rose-400'
                                }`}
                              >
                                {dw.dw_type}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-slate-300">{dw.issuer}</td>
                            <td className="px-3 py-2 text-right num text-slate-200">
                              {dw.dw_price.toFixed(2)}
                            </td>
                            <td className="px-3 py-2 text-right num text-slate-300">
                              {dw.dw_volume > 0 ? dw.dw_volume.toLocaleString() : '-'}
                            </td>
                            <td className="px-3 py-2 text-right num text-slate-200">
                              {dw.gearing.toFixed(2)}x
                            </td>
                            <td className="px-3 py-2 text-center text-slate-300">{dw.moneyness}</td>
                            <td className="px-3 py-2 text-right num text-slate-400">{dw.expiry_date}</td>
                            <td className={`px-4 py-2 text-right num font-medium ${
                              dw.days_remaining <= 30
                                ? 'text-amber-400'
                                : 'text-slate-300'
                            }`}>
                              {dw.days_remaining}d
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
