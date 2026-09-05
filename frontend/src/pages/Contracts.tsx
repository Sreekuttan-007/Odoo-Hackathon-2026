import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { Contract, EmployeeMinimal } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { ContractFormModal } from '../components/ContractFormModal';
import { useToast, ToastViewport } from '../components/Toast';
import { Button } from '../components/ui/Button';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonTable } from '../components/ui/Skeleton';
import { formatWage, formatDate } from '../lib/format';
import { Search, Plus, FileText, X } from 'lucide-react';

const HR_ROLES = ['HR_MANAGER', 'HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];

export function Contracts() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toasts, push } = useToast();
  const canManage = !!user && HR_ROLES.includes(user.role);

  const employeeId = searchParams.get('employee_id');
  const [filterEmployee, setFilterEmployee] = useState<EmployeeMinimal | null>(null);

  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const fetchContracts = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (employeeId) params.employee_id = employeeId;
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
      const res = await api.get('/contracts', { params });
      setContracts(res.data);
      if (res.data.length > 0 && employeeId) {
        setFilterEmployee(res.data[0].employee);
      }
    } finally {
      setLoading(false);
    }
  }, [employeeId, search, statusFilter]);

  useEffect(() => {
    if (employeeId) {
      api.get(`/employees/${employeeId}`).then(res => setFilterEmployee(res.data)).catch(() => setFilterEmployee(null));
    } else {
      setFilterEmployee(null);
    }
  }, [employeeId]);

  useEffect(() => {
    const t = setTimeout(fetchContracts, 250);
    return () => clearTimeout(t);
  }, [fetchContracts]);

  const clearEmployeeFilter = () => {
    searchParams.delete('employee_id');
    setSearchParams(searchParams);
  };

  const hasFilters = !!(search || statusFilter || employeeId);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Contracts"
        description="Employment terms, wage and validity history."
        action={canManage && (
          <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
            <Plus className="w-4 h-4" /> New Contract
          </Button>
        )}
      />

      {employeeId && filterEmployee && (
        <div className="inline-flex items-center gap-2 bg-brand-50 border border-brand-100 text-brand-800 text-sm px-3 py-1.5 rounded-full">
          Filtered by: <strong className="font-medium">{filterEmployee.first_name} {filterEmployee.last_name}</strong>
          <button onClick={clearEmployeeFilter} className="hover:text-brand-900"><X className="w-3.5 h-3.5" /></button>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-[var(--shadow-elevation)]">
        <div className="p-3.5 border-b border-gray-100 flex flex-col sm:flex-row gap-3 items-center justify-between">
          <div className="relative w-full sm:w-96">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-3.5 w-3.5 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Search by reference…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="block w-full h-9 pl-9 pr-3 border border-gray-300 rounded-md bg-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 text-sm"
            />
          </div>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="w-full sm:w-56 h-9 rounded-md border border-gray-300 px-2.5 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500">
            <option value="">All Statuses</option>
            <option value="RUNNING">Running</option>
            <option value="UPCOMING">Upcoming</option>
            <option value="EXPIRED">Expired</option>
          </select>
        </div>

        {loading ? (
          <SkeletonTable rows={5} cols={6} />
        ) : contracts.length === 0 ? (
          <EmptyState
            icon={FileText}
            title={employeeId && filterEmployee ? `${filterEmployee.first_name} has no contracts yet.` : hasFilters ? 'No contracts match your filters.' : 'No contracts yet.'}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Contract</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Employee</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Start</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">End</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Wage / Month</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {contracts.map(c => (
                  <tr key={c.id} onClick={() => navigate(`/contracts/${c.id}`)} className={`hover:bg-gray-50 cursor-pointer transition-colors ${c.status === 'EXPIRED' ? 'text-gray-400' : ''}`}>
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{c.reference}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{c.employee.first_name} {c.employee.last_name}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{formatDate(c.start_date)}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{c.end_date ? formatDate(c.end_date) : 'Open'}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{formatWage(c.wage_monthly, c.currency)}</td>
                    <td className="px-6 py-3 whitespace-nowrap"><StatusBadge status={c.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <ContractFormModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        fixedEmployee={filterEmployee || undefined}
        onSaved={() => { fetchContracts(); push('Contract created.'); }}
      />
      <ToastViewport toasts={toasts} />
    </div>
  );
}
