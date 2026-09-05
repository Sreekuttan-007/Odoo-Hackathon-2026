const TONE: Record<string, string> = {
  ACTIVE: 'bg-brand-50 text-brand-700',
  RUNNING: 'bg-brand-50 text-brand-700',
  APPROVED: 'bg-brand-50 text-brand-700',
  COMPLETED: 'bg-gray-100 text-gray-500',
  INACTIVE: 'bg-gray-100 text-gray-500',
  EXPIRED: 'bg-gray-100 text-gray-500',
  DRAFT: 'bg-gray-100 text-gray-500',
  UPCOMING: 'bg-warning-50 text-warning-700',
  TO_APPROVE: 'bg-warning-50 text-warning-700',
  MISSING_CHECKOUT: 'bg-danger-50 text-danger-700',
  REFUSED: 'bg-danger-50 text-danger-700',
  COMPUTED: 'bg-info-50 text-info-700',
  VALIDATED: 'bg-info-50 text-info-700',
  PAID: 'bg-brand-50 text-brand-700',
};

const DOT: Record<string, string> = {
  ACTIVE: 'bg-brand-500',
  RUNNING: 'bg-brand-500',
  APPROVED: 'bg-brand-500',
  COMPLETED: 'bg-gray-400',
  INACTIVE: 'bg-gray-400',
  EXPIRED: 'bg-gray-400',
  DRAFT: 'bg-gray-400',
  UPCOMING: 'bg-warning-500',
  TO_APPROVE: 'bg-warning-500',
  MISSING_CHECKOUT: 'bg-danger-500',
  REFUSED: 'bg-danger-500',
  COMPUTED: 'bg-info-500',
  VALIDATED: 'bg-info-500',
  PAID: 'bg-brand-500',
};

// Only statuses that need a human to act right now get the pulse —
// motion as a functional signal, not decoration on every badge.
const PULSING = new Set(['TO_APPROVE', 'MISSING_CHECKOUT']);

const LABELS: Record<string, string> = {
  ACTIVE: 'Active',
  RUNNING: 'Running',
  APPROVED: 'Approved',
  COMPLETED: 'Completed',
  INACTIVE: 'Inactive',
  EXPIRED: 'Expired',
  DRAFT: 'Draft',
  UPCOMING: 'Upcoming',
  TO_APPROVE: 'To Approve',
  MISSING_CHECKOUT: 'Missing Checkout',
  REFUSED: 'Refused',
  COMPUTED: 'Computed',
  VALIDATED: 'Validated',
  PAID: 'Paid',
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${TONE[status] || 'bg-gray-100 text-gray-500'}`}>
      <span className="relative flex h-1.5 w-1.5">
        {PULSING.has(status) && (
          <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${DOT[status]}`} />
        )}
        <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${DOT[status] || 'bg-gray-400'}`} />
      </span>
      {LABELS[status] || status}
    </span>
  );
}
