import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import type { Payslip } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { SectionCard } from '../components/ui/SectionCard';
import { DetailField } from '../components/ui/DetailField';
import { SkeletonDetail } from '../components/ui/Skeleton';
import { Button } from '../components/ui/Button';
import { formatDate, formatMoney } from '../lib/format';
import { openPayslipPdf } from '../lib/pdf';
import { ArrowLeft, FileDown, AlertTriangle, Calendar, Clock, Building2 } from 'lucide-react';

export function PayslipDetail() {
  const { payslipId } = useParams();
  const navigate = useNavigate();

  const [payslip, setPayslip] = useState<Payslip | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    api.get(`/payroll/payslips/${payslipId}`)
      .then(res => setPayslip(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [payslipId]);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await openPayslipPdf(Number(payslipId));
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-5 max-w-3xl">
        <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
        <SkeletonDetail />
      </div>
    );
  }

  if (error || !payslip) {
    return (
      <div className="text-center py-16">
        <h2 className="text-base font-semibold text-gray-800">Payslip not found</h2>
        <Button variant="ghost" className="mt-4" onClick={() => navigate('/payroll/payslips')}>← Back to Payslips</Button>
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-3xl">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back
      </button>

      <SectionCard>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Payslip</p>
            <h1 className="text-lg font-semibold text-gray-900 mt-0.5">{payslip.employee.first_name} {payslip.employee.last_name}</h1>
            <p className="text-sm text-gray-500">{payslip.salary_structure.name} · {formatDate(payslip.period_start)} — {formatDate(payslip.period_end)}</p>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={payslip.status} />
            <Button variant="secondary" size="sm" loading={downloading} onClick={handleDownload}>
              <FileDown className="w-3.5 h-3.5" /> PDF
            </Button>
          </div>
        </div>

        {payslip.warnings.length > 0 && (
          <div className="mt-4 space-y-2">
            {payslip.warnings.map(w => (
              <div key={w.id} className={`flex items-start gap-2 text-sm p-2.5 rounded-md ${w.severity === 'BLOCKER' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'}`}>
                <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" /><span>{w.message}</span>
              </div>
            ))}
          </div>
        )}

        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-6">
          <DetailField icon={Building2} label="Pay Run" valueNode={<Link to={`/payroll/payruns/${payslip.payrun_id}`} className="text-sm text-brand-600 hover:text-brand-700 font-medium">{payslip.payrun_reference}</Link>} />
          <DetailField icon={Calendar} label="Worked Days" value={payslip.worked_days !== null ? `${payslip.worked_days} / ${payslip.expected_work_days}` : undefined} />
          <DetailField icon={Clock} label="Worked Hours" value={payslip.worked_hours !== null ? `${payslip.worked_hours}h` : undefined} />
        </div>
      </SectionCard>

      <SectionCard padded={false}>
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-900">Salary Computation</h2>
        </div>
        {payslip.lines.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500">No computation available yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Rule</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Category</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Base / Rate</th>
                  <th className="px-6 py-2.5 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {payslip.lines.map(l => (
                  <tr key={l.id}>
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{l.rule_name_snapshot} <span className="text-gray-400 font-mono text-xs">({l.rule_code_snapshot})</span></td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600 capitalize">{l.category_snapshot.toLowerCase()}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-500">{l.base_description_snapshot || '—'}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-right font-medium text-gray-900">{formatMoney(l.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="border-t border-gray-100 px-6 py-4 space-y-2">
          <div className="flex justify-between text-sm"><span className="text-gray-600">Basic</span><span className="text-gray-900">{formatMoney(payslip.basic)}</span></div>
          <div className="flex justify-between text-sm"><span className="text-gray-600">Allowances</span><span className="text-gray-900">{formatMoney(payslip.allowances)}</span></div>
          <div className="flex justify-between text-sm font-medium border-t border-gray-100 pt-2"><span className="text-gray-700">Gross Salary</span><span className="text-gray-900">{formatMoney(payslip.gross)}</span></div>
          <div className="flex justify-between text-sm"><span className="text-gray-600">Deductions</span><span className="text-red-600">−{formatMoney(payslip.deductions)}</span></div>
          <div className="flex justify-between text-base font-semibold border-t border-gray-200 pt-2 mt-1"><span className="text-gray-900">Net Salary</span><span className="text-brand-700">{formatMoney(payslip.net)}</span></div>
        </div>
      </SectionCard>
    </div>
  );
}
