import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import type { SalaryStructure, EligibleEmployee } from '../types';
import { SearchableSelect } from '../components/SearchableSelect';
import { Button } from '../components/ui/Button';
import { SectionCard } from '../components/ui/SectionCard';
import { PageHeader } from '../components/ui/PageHeader';
import { formatMoney } from '../lib/format';
import { ArrowLeft, AlertTriangle, Search, Check } from 'lucide-react';

const inputClass = 'block w-full h-9 px-3 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500';

export function PayrunWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2>(1);

  const [structures, setStructures] = useState<SalaryStructure[]>([]);
  const [structureId, setStructureId] = useState<number | null>(null);
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');

  const [candidates, setCandidates] = useState<EligibleEmployee[]>([]);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [search, setSearch] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/payroll/structures', { params: { is_active: true } }).then(res => setStructures(res.data));
  }, []);

  const selectedStructure = structures.find(s => s.id === structureId);

  const handleContinue = async () => {
    if (!structureId || !periodStart || !periodEnd) return;
    setLoadingCandidates(true);
    setError('');
    try {
      const res = await api.get('/payroll/payruns/eligible-employees', {
        params: { salary_structure_id: structureId, period_start: periodStart, period_end: periodEnd },
      });
      setCandidates(res.data);
      setSelected(new Set());
      setStep(2);
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to load eligible employees.');
    } finally {
      setLoadingCandidates(false);
    }
  };

  const toggle = (employeeId: number, eligible: boolean) => {
    if (!eligible) return;
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(employeeId)) next.delete(employeeId); else next.add(employeeId);
      return next;
    });
  };

  const handleCreate = async () => {
    setCreating(true);
    setError('');
    try {
      const res = await api.post('/payroll/payruns', {
        salary_structure_id: structureId, period_start: periodStart, period_end: periodEnd,
        employee_ids: Array.from(selected),
      });
      navigate(`/payroll/payruns/${res.data.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to create Payrun.');
    } finally {
      setCreating(false);
    }
  };

  const filteredCandidates = candidates.filter(c =>
    `${c.employee.first_name} ${c.employee.last_name}`.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-5 max-w-3xl">
      <button onClick={() => navigate('/payroll/payruns')} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Payruns
      </button>

      <PageHeader title="New Payrun" description={step === 1 ? 'Step 1 of 2 · Payroll Scope' : `Step 2 of 2 · Select Employees`} />

      {error && (
        <div className="flex items-start gap-2 text-sm text-danger-700 bg-danger-50 border border-danger-100 p-3 rounded-md">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" /><span>{error}</span>
        </div>
      )}

      {step === 1 ? (
        <SectionCard>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Salary Structure</label>
              <SearchableSelect
                value={structureId}
                onChange={setStructureId}
                options={structures.map(s => ({ id: s.id, label: s.name, sublabel: `${s.rule_count} rules` }))}
                placeholder="Select structure"
                clearable={false}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Period Start</label>
                <input type="date" value={periodStart} onChange={e => setPeriodStart(e.target.value)} className={inputClass} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Period End</label>
                <input type="date" value={periodEnd} onChange={e => setPeriodEnd(e.target.value)} className={inputClass} />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
              <Button variant="secondary" onClick={() => navigate('/payroll/payruns')}>Cancel</Button>
              <Button variant="primary" loading={loadingCandidates} disabled={!structureId || !periodStart || !periodEnd} onClick={handleContinue}>
                Continue →
              </Button>
            </div>
          </div>
        </SectionCard>
      ) : (
        <SectionCard padded={false}>
          <div className="px-6 py-4 border-b border-gray-100">
            <p className="text-sm text-gray-600">{selectedStructure?.name} · {periodStart} — {periodEnd}</p>
            <div className="relative mt-3">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search employees…"
                className="w-full h-9 pl-9 pr-3 rounded-md border border-gray-300 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500" />
            </div>
          </div>
          <div className="max-h-96 overflow-y-auto divide-y divide-gray-50">
            {filteredCandidates.map(c => (
              <div
                key={c.employee.id}
                onClick={() => toggle(c.employee.id, c.eligible)}
                className={`flex items-center justify-between px-6 py-3 ${c.eligible ? 'cursor-pointer hover:bg-gray-50' : 'opacity-60 cursor-not-allowed'} transition-colors`}
              >
                <div className="flex items-center gap-3">
                  <div className={`h-4 w-4 rounded border flex items-center justify-center shrink-0 ${selected.has(c.employee.id) ? 'bg-brand-600 border-brand-600' : 'border-gray-300'}`}>
                    {selected.has(c.employee.id) && <Check className="w-3 h-3 text-white" />}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{c.employee.first_name} {c.employee.last_name}</p>
                    {c.working_schedule_summary && <p className="text-xs text-gray-400">{c.working_schedule_summary}</p>}
                  </div>
                </div>
                <div className="text-right">
                  {c.eligible ? (
                    <span className="text-sm font-medium text-gray-900">{c.wage_monthly ? formatMoney(c.wage_monthly) : '—'}</span>
                  ) : (
                    <span className="text-xs text-danger-600">Ineligible — {c.reason}</span>
                  )}
                </div>
              </div>
            ))}
            {filteredCandidates.length === 0 && (
              <div className="p-8 text-center text-sm text-gray-500">No employees match your search.</div>
            )}
          </div>
          <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
            <span className="text-sm text-gray-600">{selected.size} employee{selected.size === 1 ? '' : 's'} selected</span>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setStep(1)}>← Back</Button>
              <Button variant="primary" loading={creating} disabled={selected.size === 0} onClick={handleCreate}>Create Payrun</Button>
            </div>
          </div>
        </SectionCard>
      )}
    </div>
  );
}
