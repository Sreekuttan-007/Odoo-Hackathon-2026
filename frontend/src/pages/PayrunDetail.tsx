import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import type { Payrun, PayslipSummary, Payslip } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { SectionCard } from '../components/ui/SectionCard';
import { SkeletonDetail } from '../components/ui/Skeleton';
import { Button } from '../components/ui/Button';
import { useToast, ToastViewport } from '../components/Toast';
import { formatDate, formatMoney } from '../lib/format';
import { ArrowLeft, Calculator, ShieldCheck, Banknote, AlertTriangle, CheckCircle2, FileDown } from 'lucide-react';
import { openPayslipPdf } from '../lib/pdf';

export function PayrunDetail() {
  const { payrunId } = useParams();
  const navigate = useNavigate();
  const { toasts, push } = useToast();

  const [payrun, setPayrun] = useState<Payrun | null>(null);
  const [payslips, setPayslips] = useState<PayslipSummary[]>([]);
  const [details, setDetails] = useState<Record<number, Payslip>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [acting, setActing] = useState(false);
  const [blockers, setBlockers] = useState<{ employee: string; messages: string[] }[] | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const [payrunRes, payslipsRes] = await Promise.all([
        api.get(`/payroll/payruns/${payrunId}`),
        api.get(`/payroll/payslips`, { params: { payrun_id: payrunId } }),
      ]);
      setPayrun(payrunRes.data);
      setPayslips(payslipsRes.data);

      const withWarnings = payslipsRes.data.filter((p: PayslipSummary) => p.warning_count > 0);
      if (withWarnings.length > 0) {
        const detailResults = await Promise.all(withWarnings.map((p: PayslipSummary) => api.get(`/payroll/payslips/${p.id}`)));
        setDetails(Object.fromEntries(detailResults.map(r => [r.data.id, r.data])));
      } else {
        setDetails({});
      }
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [payrunId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const runAction = async (action: 'compute' | 'validate' | 'mark-paid') => {
    setActing(true);
    setBlockers(null);
    try {
      await api.post(`/payroll/payruns/${payrunId}/${action}`);
      await fetchAll();
      push(action === 'compute' ? 'Payroll computed.' : action === 'validate' ? 'Payrun validated.' : 'Payrun marked paid.');
    } catch (err: any) {
      const detail = err.response?.data?.detail?.error;
      if (detail?.code === 'VALIDATION_BLOCKED') {
        setBlockers(detail.details?.blockers?.map((b: any) => ({ employee: `${b.employee.first_name} ${b.employee.last_name}`, messages: b.messages })) || []);
        await fetchAll();
      }
      push(detail?.message || `Failed to ${action}.`, 'error');
    } finally {
      setActing(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-5 max-w-4xl">
        <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
        <SkeletonDetail />
      </div>
    );
  }

  if (error || !payrun) {
    return (
      <div className="text-center py-16">
        <h2 className="text-base font-semibold text-gray-800">Payrun not found</h2>
        <Button variant="ghost" className="mt-4" onClick={() => navigate('/payroll/payruns')}>← Back to Payruns</Button>
      </div>
    );
  }

  const allWarnings = Object.values(details).flatMap(p => p.warnings.map(w => ({ employee: p.employee, warning: w })));

  return (
    <div className="space-y-5 max-w-4xl">
      <button onClick={() => navigate('/payroll/payruns')} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Payruns
      </button>

      <SectionCard>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">{payrun.reference}</p>
            <h1 className="text-lg font-semibold text-gray-900 mt-0.5">{formatDate(payrun.period_start)} – {formatDate(payrun.period_end)}</h1>
            <p className="text-sm text-gray-500">{payrun.salary_structure.name}</p>
          </div>
          <StatusBadge status={payrun.status} />
        </div>

        <div className="mt-5 grid grid-cols-4 gap-4 rounded-lg border border-gray-100 bg-gray-50/60 p-4">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Employees</p>
            <p className="text-lg font-semibold text-gray-900">{payrun.employee_count}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Gross</p>
            <p className="text-lg font-semibold text-gray-900">{formatMoney(payrun.total_gross)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Net</p>
            <p className="text-lg font-semibold text-brand-700">{formatMoney(payrun.total_net)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Warnings</p>
            <p className={`text-lg font-semibold ${payrun.warning_count > 0 ? 'text-amber-700' : 'text-gray-900'}`}>{payrun.warning_count}</p>
          </div>
        </div>

        <div className="mt-5 flex gap-2">
          {payrun.status === 'DRAFT' && (
            <Button variant="primary" loading={acting} onClick={() => runAction('compute')}><Calculator className="w-3.5 h-3.5" /> Compute</Button>
          )}
          {payrun.status === 'COMPUTED' && (
            <>
              <Button variant="secondary" loading={acting} onClick={() => runAction('compute')}><Calculator className="w-3.5 h-3.5" /> Recompute</Button>
              <Button variant="primary" loading={acting} onClick={() => runAction('validate')}><ShieldCheck className="w-3.5 h-3.5" /> Validate</Button>
            </>
          )}
          {payrun.status === 'VALIDATED' && (
            <Button variant="primary" loading={acting} onClick={() => runAction('mark-paid')}><Banknote className="w-3.5 h-3.5" /> Mark Paid</Button>
          )}
        </div>

        {blockers && blockers.length > 0 && (
          <div className="mt-4 space-y-2">
            {blockers.map((b, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-red-700 bg-red-50 border border-red-100 p-3 rounded-md">
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                <span><strong>{b.employee}</strong>: {b.messages.join(' ')}</span>
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      {payrun.status !== 'DRAFT' && (
        <SectionCard>
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Payroll checks</h2>
          {allWarnings.length === 0 ? (
            <p className="text-sm text-green-700 flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4" /> No issues found.</p>
          ) : (
            <div className="space-y-2">
              {allWarnings.map(({ employee, warning }) => (
                <div key={warning.id} className={`flex items-start gap-2 text-sm p-2.5 rounded-md ${warning.severity === 'BLOCKER' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'}`}>
                  <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                  <span><strong>{employee.first_name} {employee.last_name}</strong>: {warning.message}</span>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      )}

      <SectionCard padded={false}>
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-900">Payslips</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Employee</th>
                <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Warning</th>
                <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Basic</th>
                <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Gross</th>
                <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Net</th>
                <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">PDF</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {payslips.map(p => (
                <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    <Link to={`/payroll/payslips/${p.id}`} className="hover:text-brand-700">{p.employee.first_name} {p.employee.last_name}</Link>
                  </td>
                  <td className="px-6 py-3 whitespace-nowrap text-sm">
                    {p.warning_count > 0 ? <span className="inline-flex items-center gap-1 text-amber-700"><AlertTriangle className="w-3.5 h-3.5" /> {p.warning_count}</span> : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{formatMoney(p.basic)}</td>
                  <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{formatMoney(p.gross)}</td>
                  <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{formatMoney(p.net)}</td>
                  <td className="px-6 py-3 whitespace-nowrap"><StatusBadge status={p.status} /></td>
                  <td className="px-6 py-3 whitespace-nowrap">
                    <button onClick={(e) => { e.stopPropagation(); openPayslipPdf(p.id); }}
                      className="text-gray-400 hover:text-brand-600" title="View PDF">
                      <FileDown className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
      <ToastViewport toasts={toasts} />
    </div>
  );
}
