import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { TimeOffType } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { TimeOffTypeFormDrawer } from '../components/TimeOffTypeFormDrawer';
import { useToast, ToastViewport } from '../components/Toast';
import { Button } from '../components/ui/Button';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonTable } from '../components/ui/Skeleton';
import { Plus, PlaneTakeoff } from 'lucide-react';

const HR_ROLES = ['HR_MANAGER', 'HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];

export function TimeOffTypes() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toasts, push } = useToast();
  const canManage = !!user && HR_ROLES.includes(user.role);

  const [types, setTypes] = useState<TimeOffType[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const fetchTypes = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/time-off/types');
      setTypes(res.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchTypes(); }, [fetchTypes]);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Time Off Types"
        description="Configuration for how each leave type behaves — not employee history."
        action={canManage && (
          <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
            <Plus className="w-4 h-4" /> New Type
          </Button>
        )}
      />

      <div className="bg-white rounded-xl border border-gray-200 shadow-[var(--shadow-elevation)]">
        {loading ? (
          <SkeletonTable rows={3} cols={5} />
        ) : types.length === 0 ? (
          <EmptyState icon={PlaneTakeoff} title="No time off types configured." description="Create a type before allocating leave." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Type</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Unit</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Allocation</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Approval</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {types.map(t => (
                  <tr key={t.id} onClick={() => navigate(`/time-off/types/${t.id}`)} className="hover:bg-gray-50 cursor-pointer transition-colors">
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                      <span className="inline-flex items-center gap-2">
                        {t.display_color && <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: t.display_color }} />}
                        {t.name}
                      </span>
                    </td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600 capitalize">{t.unit.toLowerCase()}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{t.requires_allocation ? 'Required' : 'Not required'}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600 capitalize">{t.approval_policy.toLowerCase()}</td>
                    <td className="px-6 py-3 whitespace-nowrap"><StatusBadge status={t.is_active ? 'ACTIVE' : 'INACTIVE'} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <TimeOffTypeFormDrawer isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} onSaved={() => { fetchTypes(); push('Time Off Type created.'); }} />
      <ToastViewport toasts={toasts} />
    </div>
  );
}
