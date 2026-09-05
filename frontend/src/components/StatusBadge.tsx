const DOT: Record<string, string> = {
  ACTIVE: 'bg-green-500',
  RUNNING: 'bg-green-500',
  APPROVED: 'bg-green-500',
  COMPLETED: 'bg-gray-400',
  INACTIVE: 'bg-gray-400',
  EXPIRED: 'bg-gray-400',
  DRAFT: 'bg-gray-400',
  UPCOMING: 'bg-amber-500',
  TO_APPROVE: 'bg-amber-500',
  MISSING_CHECKOUT: 'bg-red-500',
  REFUSED: 'bg-red-500',
  COMPUTED: 'bg-blue-500',
  VALIDATED: 'bg-indigo-500',
  PAID: 'bg-green-500',
};

const TEXT: Record<string, string> = {
  ACTIVE: 'text-green-700',
  RUNNING: 'text-green-700',
  APPROVED: 'text-green-700',
  COMPLETED: 'text-gray-500',
  INACTIVE: 'text-gray-500',
  EXPIRED: 'text-gray-500',
  DRAFT: 'text-gray-500',
  UPCOMING: 'text-amber-700',
  TO_APPROVE: 'text-amber-700',
  MISSING_CHECKOUT: 'text-red-700',
  REFUSED: 'text-red-700',
  COMPUTED: 'text-blue-700',
  VALIDATED: 'text-indigo-700',
  PAID: 'text-green-700',
};

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
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${TEXT[status] || 'text-gray-500'}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${DOT[status] || 'bg-gray-400'}`} />
      {LABELS[status] || status}
    </span>
  );
}
