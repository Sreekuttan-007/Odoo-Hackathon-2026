export function formatWage(wage: string, currency: string): string {
  const n = parseFloat(wage);
  const formatted = new Intl.NumberFormat('en-IN').format(n);
  const symbol = currency === 'INR' ? '₹' : `${currency} `;
  return `${symbol}${formatted} / month`;
}

export function formatDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

export function formatPeriod(start: string, end: string | null): string {
  return `${formatDate(start)} — ${end ? formatDate(end) : 'Present'}`;
}

const COMPANY_TIME_ZONE = 'Asia/Kolkata';

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', timeZone: COMPANY_TIME_ZONE,
  });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: COMPANY_TIME_ZONE,
  });
}

export function formatMinutes(minutes: number | null): string {
  if (minutes === null) return '—';
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${h}h ${String(m).padStart(2, '0')}m`;
}

export function formatAmount(amount: string, unit: 'DAYS' | 'HOURS'): string {
  const n = parseFloat(amount);
  const trimmed = Number.isInteger(n) ? String(n) : n.toFixed(2);
  const noun = unit === 'DAYS' ? 'day' : 'hour';
  return `${trimmed} ${noun}${n === 1 ? '' : 's'}`;
}
