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
