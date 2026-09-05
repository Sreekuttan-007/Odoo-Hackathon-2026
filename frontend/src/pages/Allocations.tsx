import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { TimeOffAllocation, EmployeeMinimal } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { AllocationFormDrawer } from '../components/AllocationFormDrawer';
import { useToast, ToastViewport } from '../components/Toast';
import { Button } from '../components/ui/Button';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonTable } from '../components/ui/Skeleton';
import { Plus, PlaneTakeoff, X } from 'lucide-react';

const HR_ROLES = ['HR_MANAGER', 'HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];

export function Allocations() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toasts, push } = useToast();
  const canManage = !!user && HR_ROLES.includes(user.role);

  const employeeId = searchParams.get('employee_id');
  const [filterEmployee, setFilterEmployee] = useState<EmployeeMinimal | null>(null);

  const [allocations, setAllocations] = useState<TimeOffAllocation[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const fetchAllocations = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (employeeId) params.employee_id = employeeId;
      if (statusFilter) params.status = statusFilter;
      const res = await api.get('/time-off/allocations', { params });
      setAllocations(res.data);
      if (res.data.length > 0 && employeeId) setFilterEmployee(res.data[0].employee);
    } finally {
      setLoading(false);
    }
  }, [employeeId, statusFilter]);

  useEffect(() => {
    if (employeeId) {
      api.get(`/employees/${employeeId}`).then(res => setFilterEmployee(res.data)).catch(() => setFilterEmployee(null));
    } else {
      setFilterEmployee(null);
    }
  }, [employeeId]);

  useEffect(() => { fetchAllocations(); }, [fetchAllocations]);

  const clearEmployeeFilter = () => {
    searchParams.delete('employee_id');
    setSearchParams(searchParams);
  };

  return (
    <div className="space-y-5">
      <PageHeader
        title="Allocations"
        description="Leave entitlement, taken and remaining balance per employee."
        action={canManage && (
          <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
            <Plus className="w-4 h-4" /> New Allocation
          </Button>
        )}
      />

      {employeeId && filterEmployee && (
        <div className="inline-flex items-center gap-2 bg-brand-50 border border-brand-100 text-brand-800 text-sm px-3 py-1.5 rounded-full">
          Employee: <strong className="font-medium">{filterEmployee.first_name} {filterEmployee.last_name}</strong>
          <button onClick={clearEmployeeFilter} className="hover:text-brand-900"><X className="w-3.5 h-3.5" /></button>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-[var(--shadow-elevation)]">
        <div className="p-3.5 border-b border-gray-100 flex items-center justify-between">
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="h-9 rounded-md border border-gray-300 px-2.5 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500">
            <option value="">All Statuses</option>
            <option value="TO_APPROVE">To Approve</option>
            <option value="APPROVED">Approved</option>
            <option value="REFUSED">Refused</option>
          </select>
        </div>

        {loading ? (
          <SkeletonTable rows={4} cols={6} />
        ) : allocations.length === 0 ? (
          <EmptyState icon={PlaneTakeoff} title={employeeId && filterEmployee ? `No allocations for ${filterEmployee.first_name}.` : 'No allocations found for this period.'} />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Employee</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Type</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Allocated</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Taken</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Remaining</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {allocations.map(a => (
                  <tr key={a.id} onClick={() => navigate(`/time-off/allocations/${a.id}`)} className="hover:bg-gray-50 cursor-pointer transition-colors">
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{a.employee.first_name} {a.employee.last_name}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{a.time_off_type.name}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{a.allocated_amount}{a.time_off_type.unit === 'DAYS' ? 'd' : 'h'}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{a.taken_amount}{a.time_off_type.unit === 'DAYS' ? 'd' : 'h'}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-semibold text-gray-900">{a.remaining_amount}{a.time_off_type.unit === 'DAYS' ? 'd' : 'h'}</td>
                    <td className="px-6 py-3 whitespace-nowrap"><StatusBadge status={a.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <AllocationFormDrawer
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        fixedEmployee={filterEmployee || undefined}
        onSaved={() => { fetchAllocations(); push('Allocation created.'); }}
      />
      <ToastViewport toasts={toasts} />
    </div>
  );
}
