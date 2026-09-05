const TONE: Record<string, string> = {
  ACTIVE: 'bg-green-50 text-green-700',
  RUNNING: 'bg-green-50 text-green-700',
  APPROVED: 'bg-green-50 text-green-700',
  COMPLETED: 'bg-gray-100 text-gray-500',
  INACTIVE: 'bg-gray-100 text-gray-500',
  EXPIRED: 'bg-gray-100 text-gray-500',
  DRAFT: 'bg-gray-100 text-gray-500',
  UPCOMING: 'bg-amber-50 text-amber-700',
  TO_APPROVE: 'bg-amber-50 text-amber-700',
  MISSING_CHECKOUT: 'bg-red-50 text-red-700',
  REFUSED: 'bg-red-50 text-red-700',
  COMPUTED: 'bg-blue-50 text-blue-700',
  VALIDATED: 'bg-indigo-50 text-indigo-700',
  PAID: 'bg-green-50 text-green-700',
};

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
      <span className={`w-1.5 h-1.5 rounded-full ${DOT[status] || 'bg-gray-400'}`} />
      {LABELS[status] || status}
    </span>
  );
}
