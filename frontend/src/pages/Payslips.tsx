import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { PayslipSummary } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonTable } from '../components/ui/Skeleton';
import { formatDate, formatMoney } from '../lib/format';
import { Wallet, AlertTriangle } from 'lucide-react';

export function Payslips() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [payslips, setPayslips] = useState<PayslipSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');

  const fetchPayslips = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (statusFilter) params.status = statusFilter;
      const res = await api.get('/payroll/payslips', { params });
      setPayslips(res.data);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { fetchPayslips(); }, [fetchPayslips]);

  const isEmployee = user?.role === 'EMPLOYEE';

  return (
    <div className="space-y-5">
      <PageHeader title="Payslips" description={isEmployee ? 'Your available payslips.' : 'Every computed payslip across all payruns.'} />

      <div className="bg-white rounded-xl border border-gray-200 shadow-[var(--shadow-elevation)]">
        <div className="p-3.5 border-b border-gray-100 flex items-center justify-between">
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="h-9 rounded-md border border-gray-300 px-2.5 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500">
            <option value="">All Statuses</option>
            {!isEmployee && <option value="DRAFT">Draft</option>}
            {!isEmployee && <option value="COMPUTED">Computed</option>}
            <option value="VALIDATED">Validated</option>
            <option value="PAID">Paid</option>
          </select>
        </div>

        {loading ? (
          <SkeletonTable rows={4} cols={6} />
        ) : payslips.length === 0 ? (
          <EmptyState icon={Wallet} title={isEmployee ? "You don't have any payslips yet." : 'No payslips for this period.'} />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  {!isEmployee && <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Employee</th>}
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Warning</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Period</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Basic</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Gross</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Net</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Structure</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {payslips.map(p => (
                  <tr key={p.id} onClick={() => navigate(`/payroll/payslips/${p.id}`)} className="hover:bg-gray-50 cursor-pointer transition-colors">
                    {!isEmployee && <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{p.employee.first_name} {p.employee.last_name}</td>}
                    <td className="px-6 py-3 whitespace-nowrap text-sm">
                      {p.warning_count > 0 ? <span className="inline-flex items-center gap-1 text-warning-700"><AlertTriangle className="w-3.5 h-3.5" /> {p.warning_count}</span> : <span className="text-gray-400">—</span>}
                    </td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{formatDate(p.period_start)} – {formatDate(p.period_end)}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{formatMoney(p.basic)}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{formatMoney(p.gross)}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{formatMoney(p.net)}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{p.salary_structure.name}</td>
                    <td className="px-6 py-3 whitespace-nowrap"><StatusBadge status={p.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
