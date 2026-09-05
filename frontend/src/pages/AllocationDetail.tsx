import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { TimeOffAllocation } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { SectionCard } from '../components/ui/SectionCard';
import { DetailField } from '../components/ui/DetailField';
import { SkeletonDetail } from '../components/ui/Skeleton';
import { Button } from '../components/ui/Button';
import { useToast, ToastViewport } from '../components/Toast';
import { formatPeriod } from '../lib/format';
import { ArrowLeft, Check, X as XIcon, UserCircle2, StickyNote } from 'lucide-react';

const HR_ROLES = ['HR_MANAGER', 'HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];

export function AllocationDetail() {
  const { allocationId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toasts, push } = useToast();
  const canDecide = !!user && HR_ROLES.includes(user.role);

  const [allocation, setAllocation] = useState<TimeOffAllocation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [acting, setActing] = useState(false);

  const fetchAllocation = () => {
    setLoading(true);
    setError(false);
    api.get(`/time-off/allocations/${allocationId}`)
      .then(res => setAllocation(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(fetchAllocation, [allocationId]);

  const decide = async (action: 'approve' | 'refuse') => {
    setActing(true);
    try {
      const res = await api.post(`/time-off/allocations/${allocationId}/${action}`);
      setAllocation(res.data);
      push(action === 'approve' ? 'Allocation approved.' : 'Allocation refused.');
    } catch (err: any) {
      push(err.response?.data?.detail?.error?.message || `Failed to ${action} allocation.`, 'error');
    } finally {
      setActing(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-5 max-w-2xl">
        <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
        <SkeletonDetail />
      </div>
    );
  }

  if (error || !allocation) {
    return (
      <div className="text-center py-16">
        <h2 className="text-base font-semibold text-gray-800">Allocation not found</h2>
        <Button variant="ghost" className="mt-4" onClick={() => navigate('/time-off/allocations')}>← Back to Allocations</Button>
      </div>
    );
  }

  const unitSuffix = allocation.time_off_type.unit === 'DAYS' ? ' days' : ' hours';

  return (
    <div className="space-y-5 max-w-2xl">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back
      </button>

      <SectionCard>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Allocation</p>
            <Link to={`/employees/${allocation.employee.id}`} className="text-lg font-semibold text-gray-900 mt-0.5 hover:text-brand-700 block">
              {allocation.employee.first_name} {allocation.employee.last_name}
            </Link>
            <p className="text-sm text-gray-500">{allocation.time_off_type.name} · {allocation.description || 'No description'}</p>
          </div>
          <StatusBadge status={allocation.status} />
        </div>

        <div className="mt-5 grid grid-cols-3 gap-4 rounded-lg border border-gray-100 bg-gray-50/60 p-4">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Allocated</p>
            <p className="text-lg font-semibold text-gray-900">{allocation.allocated_amount}{unitSuffix}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Taken</p>
            <p className="text-lg font-semibold text-gray-900">{allocation.taken_amount}{unitSuffix}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Remaining</p>
            <p className="text-lg font-semibold text-brand-700">{allocation.remaining_amount}{unitSuffix}</p>
          </div>
        </div>

        {canDecide && allocation.status === 'TO_APPROVE' && (
          <div className="mt-5 flex gap-2">
            <Button variant="primary" loading={acting} onClick={() => decide('approve')}><Check className="w-3.5 h-3.5" /> Approve</Button>
            <Button variant="destructive" loading={acting} onClick={() => decide('refuse')}><XIcon className="w-3.5 h-3.5" /> Refuse</Button>
          </div>
        )}

        <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-6">
          <DetailField label="Validity" value={formatPeriod(allocation.valid_from, allocation.valid_to)} />
          <DetailField icon={UserCircle2} label="Approver" value={allocation.approver_name || undefined} />
        </div>

        <div className="mt-6 pt-5 border-t border-gray-100">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 h-7 w-7 rounded-md bg-gray-50 border border-gray-100 flex items-center justify-center shrink-0">
              <StickyNote className="w-3.5 h-3.5 text-gray-400" />
            </div>
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Description</p>
              <p className={`text-sm mt-0.5 ${allocation.description ? 'text-gray-900' : 'text-gray-400 italic'}`}>{allocation.description || 'No description.'}</p>
            </div>
          </div>
        </div>
      </SectionCard>
      <ToastViewport toasts={toasts} />
    </div>
  );
}
