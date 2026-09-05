import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { TimeOffRequest } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { SectionCard } from '../components/ui/SectionCard';
import { DetailField } from '../components/ui/DetailField';
import { SkeletonDetail } from '../components/ui/Skeleton';
import { Button } from '../components/ui/Button';
import { useToast, ToastViewport } from '../components/Toast';
import { formatDate, formatAmount } from '../lib/format';
import { ArrowLeft, Check, X as XIcon, UserCircle2, StickyNote, Wallet } from 'lucide-react';

const HR_ROLES = ['HR_MANAGER', 'HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];

export function TimeOffRequestDetail() {
  const { requestId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toasts, push } = useToast();
  const canDecide = !!user && HR_ROLES.includes(user.role);

  const [request, setRequest] = useState<TimeOffRequest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [acting, setActing] = useState(false);

  const fetchRequest = () => {
    setLoading(true);
    setError(false);
    api.get(`/time-off/requests/${requestId}`)
      .then(res => setRequest(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(fetchRequest, [requestId]);

  const decide = async (action: 'approve' | 'refuse') => {
    setActing(true);
    try {
      const res = await api.post(`/time-off/requests/${requestId}/${action}`);
      setRequest(res.data);
      push(action === 'approve' ? 'Request approved.' : 'Request refused.');
    } catch (err: any) {
      push(err.response?.data?.detail?.error?.message || `Failed to ${action} request.`, 'error');
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

  if (error || !request) {
    return (
      <div className="text-center py-16">
        <h2 className="text-base font-semibold text-gray-800">Time off request not found</h2>
        <Button variant="ghost" className="mt-4" onClick={() => navigate('/time-off/requests')}>← Back to Time Off Requests</Button>
      </div>
    );
  }

  const period = request.start_date === request.end_date
    ? formatDate(request.start_date)
    : `${formatDate(request.start_date)} – ${formatDate(request.end_date)}`;

  return (
    <div className="space-y-5 max-w-2xl">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back
      </button>

      <SectionCard>
        <div className="flex items-start justify-between">
          <div>
            <Link to={`/employees/${request.employee.id}`} className="text-lg font-semibold text-gray-900 hover:text-brand-700">
              {request.employee.first_name} {request.employee.last_name}
            </Link>
            <p className="text-sm text-gray-500">{request.time_off_type.name}</p>
            <p className="text-sm text-gray-500 mt-0.5">{period} · {formatAmount(request.duration_amount, request.time_off_type.unit)}</p>
          </div>
          <StatusBadge status={request.status} />
        </div>

        {canDecide && request.status === 'TO_APPROVE' && (
          <div className="mt-5 flex gap-2">
            <Button variant="primary" loading={acting} onClick={() => decide('approve')}><Check className="w-3.5 h-3.5" /> Approve</Button>
            <Button variant="destructive" loading={acting} onClick={() => decide('refuse')}><XIcon className="w-3.5 h-3.5" /> Refuse</Button>
          </div>
        )}

        <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-6">
          <DetailField label="Type" value={request.time_off_type.name} />
          <DetailField label="Reason" value={request.reason || undefined} />
          <DetailField icon={UserCircle2} label="Approver" value={request.approver_name || undefined} />
          <DetailField label="Status" valueNode={<StatusBadge status={request.status} />} />
        </div>

        {request.balance && (
          <div className="mt-6 pt-5 border-t border-gray-100">
            <div className="flex items-start gap-3 mb-3">
              <div className="mt-0.5 h-7 w-7 rounded-md bg-gray-50 border border-gray-100 flex items-center justify-center shrink-0">
                <Wallet className="w-3.5 h-3.5 text-gray-400" />
              </div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mt-1.5">Balance</p>
            </div>
            <div className="grid grid-cols-3 gap-4 rounded-lg border border-gray-100 bg-gray-50/60 p-4 ml-10">
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wide">Before</p>
                <p className="text-sm font-semibold text-gray-900">{formatAmount(request.balance.before, request.time_off_type.unit)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wide">Consumed</p>
                <p className="text-sm font-semibold text-gray-900">{formatAmount(request.balance.consumed, request.time_off_type.unit)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wide">Remaining</p>
                <p className="text-sm font-semibold text-brand-700">{formatAmount(request.balance.remaining, request.time_off_type.unit)}</p>
              </div>
            </div>
            <Link to={`/time-off/allocations/${request.balance.allocation_id}`} className="ml-10 mt-2 inline-block text-xs text-brand-600 hover:text-brand-700 font-medium">
              View allocation used →
            </Link>
          </div>
        )}

        <div className="mt-6 pt-5 border-t border-gray-100">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 h-7 w-7 rounded-md bg-gray-50 border border-gray-100 flex items-center justify-center shrink-0">
              <StickyNote className="w-3.5 h-3.5 text-gray-400" />
            </div>
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Reason</p>
              <p className={`text-sm mt-0.5 ${request.reason ? 'text-gray-900' : 'text-gray-400 italic'}`}>{request.reason || 'No reason given.'}</p>
            </div>
          </div>
        </div>
      </SectionCard>
      <ToastViewport toasts={toasts} />
    </div>
  );
}
