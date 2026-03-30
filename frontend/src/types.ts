// types.ts — TypeScript interfaces for DW Dashboard

export interface DWItem {
  dw_code: string;
  dw_type: 'Call' | 'Put';
  issuer: string;
  dw_price: number;
  underlying: string;
  gearing: number;
  moneyness: string;
  expiry_date: string;
  days_remaining: number;
  dw_volume: number;
}

export interface StockSignal {
  symbol: string;
  last_price: number;
  change_pct: number;
  today_volume: number;
  avg_5d_volume: number;
  volume_ratio: number;
  strength: string; 
  signal_type: string;
  signal_value: number;
  dw_list: DWItem[];
  updated_at: string;
  sparkline: number[];
}

export interface DashboardPayload {
  timestamp: string;
  market_status: 'OPEN' | 'CLOSED' | 'PRE-OPEN';
  dw_universe_count: number;
  dw_all_count: number;
  signal_count: number;
  signals: StockSignal[];
}

export interface WSMessage {
  type: 'snapshot' | 'ping';
  payload?: DashboardPayload;
}

export interface SignalPulse {
  time: string;
  ratio: number;
  strength: string;
  signal_type: string;
  signal_value: number;
  match_price?: number;
  day_high_price?: number;
  close_price?: number;
  profit_high_pct?: number;
  profit_close_pct?: number;
}

export interface SignalRecord {
  id: string;
  date: string;
  symbol: string;
  first_seen: string;
  last_seen: string;
  pulses: SignalPulse[];
  max_ratio: number;
  strength: string;
  last_price: number;
  change_pct: number;
  avg_5d_volume: number;
  today_volume: number;
  dw_count: number;
  dw_codes: string[];
  simultaneous_count: number;
  is_market_wide: boolean;
}

export interface SignalHistoryResponse {
  date: string;
  count: number;
  records: SignalRecord[];
  available_dates: string[];
}

export interface DWUniverseResponse {
  underlying_count: number;
  total_dw_count: number;
  data: Record<string, DWItem[]>;
}
