import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import type { Payrun } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { Button } from '../components/ui/Button';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonTable } from '../components/ui/Skeleton';
import { formatDate, formatMoney } from '../lib/format';
import { Plus, Wallet, AlertTriangle } from 'lucide-react';

export function Payruns() {
  const navigate = useNavigate();
  const [payruns, setPayruns] = useState<Payrun[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPayruns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/payroll/payruns');
      setPayruns(res.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPayruns(); }, [fetchPayruns]);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Payruns"
        description="Payroll batches for a period and selected employees."
        action={
          <Button variant="primary" onClick={() => navigate('/payroll/payruns/new')}>
            <Plus className="w-4 h-4" /> New Payrun
          </Button>
        }
      />

      <div className="bg-white rounded-xl border border-gray-200 shadow-[var(--shadow-elevation)]">
        {loading ? (
          <SkeletonTable rows={4} cols={6} />
        ) : payruns.length === 0 ? (
          <EmptyState icon={Wallet} title="No payruns yet." description="Create your first payroll period." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Period</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Structure</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Employees</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Net</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Warnings</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {payruns.map(p => (
                  <tr key={p.id} onClick={() => navigate(`/payroll/payruns/${p.id}`)} className="hover:bg-gray-50 cursor-pointer transition-colors">
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{formatDate(p.period_start)} – {formatDate(p.period_end)}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{p.salary_structure.name}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{p.employee_count}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{formatMoney(p.total_net)}</td>
                    <td className="px-6 py-3 whitespace-nowrap"><StatusBadge status={p.status} /></td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm">
                      {p.warning_count > 0 ? (
                        <span className="inline-flex items-center gap-1 text-warning-700"><AlertTriangle className="w-3.5 h-3.5" /> {p.warning_count}</span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
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
