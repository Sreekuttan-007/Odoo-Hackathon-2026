const DOT: Record<string, string> = {
  ACTIVE: 'bg-green-500',
  RUNNING: 'bg-green-500',
  INACTIVE: 'bg-gray-400',
  EXPIRED: 'bg-gray-400',
  UPCOMING: 'bg-amber-500',
};

const TEXT: Record<string, string> = {
  ACTIVE: 'text-green-700',
  RUNNING: 'text-green-700',
  INACTIVE: 'text-gray-500',
  EXPIRED: 'text-gray-500',
  UPCOMING: 'text-amber-700',
};

const LABELS: Record<string, string> = {
  ACTIVE: 'Active',
  RUNNING: 'Running',
  INACTIVE: 'Inactive',
  EXPIRED: 'Expired',
  UPCOMING: 'Upcoming',
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${TEXT[status] || 'text-gray-500'}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${DOT[status] || 'bg-gray-400'}`} />
      {LABELS[status] || status}
    </span>
  );
}
