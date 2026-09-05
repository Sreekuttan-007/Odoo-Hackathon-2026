import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { SalaryStructure } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { SalaryStructureFormDrawer } from '../components/SalaryStructureFormDrawer';
import { useToast, ToastViewport } from '../components/Toast';
import { Button } from '../components/ui/Button';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonTable } from '../components/ui/Skeleton';
import { Plus, Wallet } from 'lucide-react';

const PAYROLL_MANAGER_ROLES = ['HR_PAYROLL_MANAGER', 'ADMIN'];

export function SalaryStructures() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toasts, push } = useToast();
  const canManage = !!user && PAYROLL_MANAGER_ROLES.includes(user.role);

  const [structures, setStructures] = useState<SalaryStructure[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const fetchStructures = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/payroll/structures');
      setStructures(res.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchStructures(); }, [fetchStructures]);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Salary Structures"
        description="Configuration — which ordered rules calculate each payslip."
        action={canManage && (
          <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
            <Plus className="w-4 h-4" /> New Structure
          </Button>
        )}
      />

      <div className="bg-white rounded-xl border border-gray-200 shadow-[var(--shadow-elevation)]">
        {loading ? (
          <SkeletonTable rows={3} cols={4} />
        ) : structures.length === 0 ? (
          <EmptyState icon={Wallet} title="No salary structures configured." description="Create a structure before running payroll." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Structure Name</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Rules</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {structures.map(s => (
                  <tr key={s.id} onClick={() => navigate(`/payroll/salary-structures/${s.id}`)} className="hover:bg-gray-50 cursor-pointer transition-colors">
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{s.name}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{s.rule_count}</td>
                    <td className="px-6 py-3 whitespace-nowrap"><StatusBadge status={s.is_active ? 'ACTIVE' : 'INACTIVE'} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <SalaryStructureFormDrawer isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} onSaved={() => { fetchStructures(); push('Salary Structure created.'); }} />
      <ToastViewport toasts={toasts} />
    </div>
  );
}
