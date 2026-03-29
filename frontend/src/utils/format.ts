// format.ts — Number and date formatting utilities for DW Dashboard

/**
 * Format volume with K/M/B suffix (1 decimal place).
 * e.g. 45200000 -> "45.2M"
 */
export function formatVolume(n: number): string {
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return n.toString();
}

/**
 * Format volume with K/M/B suffix (rounded, no decimal).
 * e.g. 45200000 -> "45M"
 */
export function formatVolumeShort(n: number): string {
  if (n >= 1e9) return Math.round(n / 1e9) + 'B';
  if (n >= 1e6) return Math.round(n / 1e6) + 'M';
  if (n >= 1e3) return Math.round(n / 1e3) + 'K';
  return n.toString();
}

/**
 * Format price to 2 decimal places.
 * e.g. 3.5 -> "3.50"
 */
export function formatPrice(n: number): string {
  return n.toFixed(2);
}

/**
 * Format change percentage with sign and % symbol.
 * e.g. 2.1 -> "+2.10%", -0.5 -> "-0.50%"
 */
export function formatChangePct(n: number): string {
  const sign = n >= 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}%`;
}

/**
 * Format volume ratio as multiplier string.
 * e.g. 3.7 -> "3.7x"
 */
export function formatRatio(n: number): string {
  return `${n.toFixed(1)}x`;
}

/**
 * Format a date string (YYYY-MM-DD) into short Thai date.
 * e.g. "2026-03-29" -> "29 มี.ค."
 */
export function formatThaiDate(str: string): string {
  const months = [
    'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.',
    'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.',
  ];
  try {
    const d = new Date(str);
    if (isNaN(d.getTime())) return str;
    return `${d.getDate()} ${months[d.getMonth()]}`;
  } catch {
    return str;
  }
}

/**
 * Format a Thai Buddhist Era year from a Gregorian date string.
 * e.g. "2026-03-29" -> "29 มี.ค. 69"
 */
export function formatThaiDateFull(str: string): string {
  const months = [
    'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.',
    'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.',
  ];
  try {
    const d = new Date(str);
    if (isNaN(d.getTime())) return str;
    const beYear = (d.getFullYear() + 543).toString().slice(-2);
    return `${d.getDate()} ${months[d.getMonth()]} ${beYear}`;
  } catch {
    return str;
  }
}

/**
 * Format a number with locale-style comma separators.
 * e.g. 1234567 -> "1,234,567"
 */
export function formatNumber(n: number): string {
  return n.toLocaleString('en-US');
}
