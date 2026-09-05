import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import type { Payrun, PayslipSummary, PreflightResult } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { SectionCard } from '../components/ui/SectionCard';
import { SkeletonDetail } from '../components/ui/Skeleton';
import { Button } from '../components/ui/Button';
import { PreflightPanel } from '../components/PreflightPanel';
import { PayrollBrief } from '../components/PayrollBrief';
import { useToast, ToastViewport } from '../components/Toast';
import { formatDate, formatMoney } from '../lib/format';
import { ArrowLeft, Calculator, ShieldCheck, Banknote, AlertTriangle, FileDown } from 'lucide-react';
import { openPayslipPdf } from '../lib/pdf';

const PREFLIGHT_PANEL_ID = 'preflight-panel';
const PREFLIGHT_STATUSES = ['COMPUTED', 'VALIDATED', 'PAID'];

export function PayrunDetail() {
  const { payrunId } = useParams();
  const navigate = useNavigate();
  const { toasts, push } = useToast();

  const [payrun, setPayrun] = useState<Payrun | null>(null);
  const [payslips, setPayslips] = useState<PayslipSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [acting, setActing] = useState(false);

  const [preflight, setPreflight] = useState<PreflightResult | null>(null);
  const [preflightLoading, setPreflightLoading] = useState(false);

  const runPreflight = useCallback(async (method: 'get' | 'post' = 'get') => {
    setPreflightLoading(true);
    try {
      const res = method === 'post'
        ? await api.post(`/payroll/payruns/${payrunId}/preflight`)
        : await api.get(`/payroll/payruns/${payrunId}/preflight`);
      setPreflight(res.data);
      return res.data as PreflightResult;
    } catch {
      setPreflight(null);
      return null;
    } finally {
      setPreflightLoading(false);
    }
  }, [payrunId]);

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
      if (PREFLIGHT_STATUSES.includes(payrunRes.data.status)) {
        await runPreflight('get');
      } else {
        setPreflight(null);
      }
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [payrunId, runPreflight]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const scrollToPreflight = () => {
    document.getElementById(PREFLIGHT_PANEL_ID)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const runAction = async (action: 'compute' | 'validate' | 'mark-paid') => {
    setActing(true);
    try {
      await api.post(`/payroll/payruns/${payrunId}/${action}`);
      await fetchAll();
      push(action === 'compute' ? 'Payroll computed.' : action === 'validate' ? 'Payrun validated.' : 'Payrun marked paid.');
    } catch (err: any) {
      const detail = err.response?.data?.detail?.error;
      if (detail?.code === 'VALIDATION_BLOCKED') {
        await runPreflight('get');
        push('Validation blocked — resolve the Preflight blockers first.', 'error');
        setTimeout(scrollToPreflight, 100);
      } else {
        push(detail?.message || `Failed to ${action}.`, 'error');
      }
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

  const blockerCount = preflight?.summary.blockers ?? 0;
  const validateBlocked = blockerCount > 0;

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
            <p className={`text-lg font-semibold ${payrun.warning_count > 0 ? 'text-warning-700' : 'text-gray-900'}`}>{payrun.warning_count}</p>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-2">
          {payrun.status === 'DRAFT' && (
            <Button variant="primary" loading={acting} onClick={() => runAction('compute')}><Calculator className="w-3.5 h-3.5" /> Compute</Button>
          )}
          {payrun.status === 'COMPUTED' && (
            <>
              <Button variant="secondary" loading={acting} onClick={() => runAction('compute')}><Calculator className="w-3.5 h-3.5" /> Recompute</Button>
              <Button
                variant="primary" loading={acting} disabled={validateBlocked}
                title={validateBlocked ? `Resolve ${blockerCount} Preflight blocker${blockerCount === 1 ? '' : 's'} before validation.` : undefined}
                onClick={() => runAction('validate')}
              >
                <ShieldCheck className="w-3.5 h-3.5" /> Validate
              </Button>
              {validateBlocked && (
                <button onClick={scrollToPreflight} className="inline-flex items-center gap-1.5 text-sm text-danger-700 hover:text-danger-800">
                  <AlertTriangle className="w-3.5 h-3.5" /> Resolve {blockerCount} blocker{blockerCount === 1 ? '' : 's'} in Preflight
                </button>
              )}
            </>
          )}
          {payrun.status === 'VALIDATED' && (
            <Button variant="primary" loading={acting} onClick={() => runAction('mark-paid')}><Banknote className="w-3.5 h-3.5" /> Mark Paid</Button>
          )}
        </div>
      </SectionCard>

      {PREFLIGHT_STATUSES.includes(payrun.status) && (
        <PreflightPanel
          result={preflight}
          loading={preflightLoading}
          onRun={() => runPreflight('post')}
          panelId={PREFLIGHT_PANEL_ID}
        />
      )}

      {payrunId && (
        <PayrollBrief payrunId={payrunId} canGenerate={PREFLIGHT_STATUSES.includes(payrun.status)} />
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
                    {p.warning_count > 0 ? <span className="inline-flex items-center gap-1 text-warning-700"><AlertTriangle className="w-3.5 h-3.5" /> {p.warning_count}</span> : <span className="text-gray-400">—</span>}
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
