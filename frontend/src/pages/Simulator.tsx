import { useState, useEffect, Fragment } from 'react';
import api from '../services/api';
import type {
  SalaryStructure, SalaryStructureDetail, SalaryRule, EligibleEmployee,
  RuleOverrideInput, SimulatorRunResponse, EmployeeSimulationResult, ComputationMethod,
} from '../types';
import { SearchableSelect } from '../components/SearchableSelect';
import { Button } from '../components/ui/Button';
import { SectionCard } from '../components/ui/SectionCard';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { formatMoney } from '../lib/format';
import {
  FlaskConical, ChevronDown, ArrowRight, RotateCcw, Trash2, AlertTriangle,
  TrendingUp, TrendingDown, Minus, Info,
} from 'lucide-react';

const inputClass = 'block w-full h-9 px-3 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500';
const selectClass = inputClass;

const STATUS_STYLE: Record<string, string> = {
  INCREASED: 'text-brand-700 bg-brand-50',
  DECREASED: 'text-danger-700 bg-danger-50',
  UNCHANGED: 'text-gray-500 bg-gray-100',
  EXCLUDED: 'text-warning-700 bg-warning-50',
};

const STATUS_ICON: Record<string, typeof TrendingUp> = {
  INCREASED: TrendingUp, DECREASED: TrendingDown, UNCHANGED: Minus, EXCLUDED: AlertTriangle,
};

interface Draft {
  computation_method: ComputationMethod;
  fixed_amount: string;
  percentage: string;
  base_code: string;
  formula_expression: string;
  quantity: string;
}

function draftFromRule(rule: SalaryRule): Draft {
  return {
    computation_method: rule.computation_method,
    fixed_amount: rule.fixed_amount ?? '',
    percentage: rule.percentage ?? '',
    base_code: rule.percentage_base ?? 'CONTRACT_WAGE',
    formula_expression: rule.formula_expression ?? '',
    quantity: rule.quantity,
  };
}

function draftToOverride(ruleId: number, draft: Draft): RuleOverrideInput {
  return {
    rule_id: ruleId,
    computation_method: draft.computation_method,
    fixed_amount: draft.computation_method === 'FIXED' ? draft.fixed_amount : undefined,
    percentage: draft.computation_method === 'PERCENTAGE' ? draft.percentage : undefined,
    base_code: draft.computation_method === 'PERCENTAGE' ? draft.base_code : undefined,
    formula_expression: draft.computation_method === 'FORMULA' ? draft.formula_expression : undefined,
    quantity: draft.quantity,
  };
}

function RuleRow({ rule, draft, onChange, earlierCodes }: {
  rule: SalaryRule; draft: Draft | null; onChange: (d: Draft | null) => void; earlierCodes: string[];
}) {
  const [expanded, setExpanded] = useState(false);
  const isOverridden = draft !== null;

  return (
    <div className={`rounded-lg border transition-colors ${isOverridden ? 'border-brand-300 bg-brand-50/40' : 'border-gray-100'}`}>
      <div className="flex items-center gap-3 px-4 py-2.5">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gray-900 text-white text-[10px] font-mono font-semibold">
          {String(rule.sequence).padStart(2, '0')}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-gray-900">{rule.name}</span>
            <span className="font-mono text-[11px] text-gray-400">{rule.code}</span>
            {isOverridden && <span className="text-[10px] font-medium uppercase tracking-wide text-brand-700 bg-brand-100 rounded-full px-2 py-0.5">Edited</span>}
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            {rule.computation_method === 'FIXED' && `Fixed ${rule.fixed_amount}`}
            {rule.computation_method === 'PERCENTAGE' && `${rule.percentage}% of ${rule.percentage_base}`}
            {rule.computation_method === 'FORMULA' && rule.formula_expression}
          </p>
        </div>
        <button
          onClick={() => { setExpanded(e => !e); if (!isOverridden && !expanded) onChange(draftFromRule(rule)); }}
          className="text-xs font-medium text-brand-600 hover:text-brand-700 shrink-0 flex items-center gap-1"
        >
          {isOverridden ? 'Edit override' : 'Try a change'} <ChevronDown className={`w-3 h-3 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </button>
        {isOverridden && (
          <button onClick={() => { onChange(null); setExpanded(false); }} className="text-xs text-gray-400 hover:text-danger-600 shrink-0">
            Revert
          </button>
        )}
      </div>

      {expanded && draft && (
        <div className="animate-load-in border-t border-gray-100 px-4 py-3 ml-9 space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Computation</label>
            <select value={draft.computation_method} onChange={e => onChange({ ...draft, computation_method: e.target.value as ComputationMethod })} className={selectClass}>
              <option value="FIXED">Fixed Amount</option>
              <option value="PERCENTAGE">Percentage</option>
              <option value="FORMULA">Formula</option>
            </select>
          </div>
          {draft.computation_method === 'FIXED' && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Amount</label>
              <input type="number" step="0.01" value={draft.fixed_amount} onChange={e => onChange({ ...draft, fixed_amount: e.target.value })} className={inputClass} />
            </div>
          )}
          {draft.computation_method === 'PERCENTAGE' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Percentage</label>
                <input type="number" step="0.01" value={draft.percentage} onChange={e => onChange({ ...draft, percentage: e.target.value })} className={inputClass} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Base</label>
                <select value={draft.base_code} onChange={e => onChange({ ...draft, base_code: e.target.value })} className={selectClass}>
                  <option value="CONTRACT_WAGE">Contract Wage</option>
                  {earlierCodes.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>
          )}
          {draft.computation_method === 'FORMULA' && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Formula Expression</label>
              <textarea value={draft.formula_expression} onChange={e => onChange({ ...draft, formula_expression: e.target.value })} rows={2}
                className="w-full px-3 py-2 rounded-md border border-gray-300 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EmployeeInspector({ result, onClose }: { result: EmployeeSimulationResult; onClose: () => void }) {
  return (
    <div className="animate-load-in border-t border-gray-100 bg-gray-50/60 px-6 py-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Component comparison — {result.employee_name}</p>
        <button onClick={onClose} className="text-xs text-gray-400 hover:text-gray-600">Close</button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] font-medium text-gray-400 uppercase tracking-wider">
              <th className="pb-1.5 pr-4">Rule</th>
              <th className="pb-1.5 pr-4">Category</th>
              <th className="pb-1.5 pr-4 text-right">Current</th>
              <th className="pb-1.5 pr-4 text-right">Simulated</th>
              <th className="pb-1.5 text-right">Δ</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {result.components.map(c => {
              const delta = (c.current_amount != null && c.simulated_amount != null)
                ? (parseFloat(c.simulated_amount) - parseFloat(c.current_amount)) : null;
              return (
                <tr key={c.rule_code} className={c.changed ? 'bg-brand-50/50' : ''}>
                  <td className="py-1.5 pr-4"><span className="font-medium text-gray-900">{c.rule_name}</span> <span className="font-mono text-[11px] text-gray-400">{c.rule_code}</span></td>
                  <td className="py-1.5 pr-4 text-gray-500">{c.category}</td>
                  <td className="py-1.5 pr-4 text-right font-mono text-gray-700">{c.current_amount ? formatMoney(c.current_amount) : '—'}</td>
                  <td className="py-1.5 pr-4 text-right font-mono text-gray-900">{c.simulated_amount ? formatMoney(c.simulated_amount) : '—'}</td>
                  <td className={`py-1.5 text-right font-mono ${delta && delta > 0 ? 'text-brand-700' : delta && delta < 0 ? 'text-danger-600' : 'text-gray-400'}`}>
                    {delta != null ? (delta === 0 ? '—' : `${delta > 0 ? '+' : ''}${formatMoney(String(delta.toFixed(2)))}`) : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function Simulator() {
  const [structures, setStructures] = useState<SalaryStructure[]>([]);
  const [structureId, setStructureId] = useState<number | null>(null);
  const [structureDetail, setStructureDetail] = useState<SalaryStructureDetail | null>(null);
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');

  const [candidates, setCandidates] = useState<EligibleEmployee[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [loadingCandidates, setLoadingCandidates] = useState(false);

  const [overrides, setOverrides] = useState<Map<number, Draft>>(new Map());
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<SimulatorRunResponse | null>(null);
  const [inspecting, setInspecting] = useState<number | null>(null);

  useEffect(() => {
    api.get('/payroll/structures', { params: { is_active: true } }).then(res => setStructures(res.data));
  }, []);

  useEffect(() => {
    setStructureDetail(null);
    setOverrides(new Map());
    setCandidates([]);
    setSelected(new Set());
    setResult(null);
    if (!structureId) return;
    api.get(`/payroll/structures/${structureId}`).then(res => setStructureDetail(res.data));
  }, [structureId]);

  const loadEligible = async () => {
    if (!structureId || !periodStart || !periodEnd) return;
    setLoadingCandidates(true);
    setError('');
    try {
      const res = await api.get('/payroll/payruns/eligible-employees', { params: { salary_structure_id: structureId, period_start: periodStart, period_end: periodEnd } });
      setCandidates(res.data);
      setSelected(new Set(res.data.filter((c: EligibleEmployee) => c.eligible).map((c: EligibleEmployee) => c.employee.id)));
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to load eligible employees.');
    } finally {
      setLoadingCandidates(false);
    }
  };

  const toggle = (id: number) => setSelected(prev => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  const runSimulation = async () => {
    if (!structureId || selected.size === 0) return;
    setRunning(true);
    setError('');
    setResult(null);
    try {
      const rule_overrides = Array.from(overrides.entries()).map(([ruleId, draft]) => draftToOverride(ruleId, draft));
      const res = await api.post('/payroll/simulator/run', {
        salary_structure_id: structureId, period_start: periodStart, period_end: periodEnd,
        employee_ids: Array.from(selected), rule_overrides,
      });
      setResult(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Simulation failed.');
    } finally {
      setRunning(false);
    }
  };

  const resetScenario = () => setOverrides(new Map());
  const discard = () => {
    if (overrides.size > 0 && !window.confirm('Discard this scenario? Any temporary rule edits will be cleared.')) return;
    setOverrides(new Map());
    setResult(null);
    setSelected(new Set());
    setStructureId(null);
    setPeriodStart('');
    setPeriodEnd('');
  };

  return (
    <div className="max-w-4xl space-y-5">
      <PageHeader
        eyebrow="Payroll Simulator"
        title="What if we changed this Salary Rule?"
        description="Reruns the real Salary Rule engine against a temporary scenario. Nothing here is saved."
      />

      <div className="rounded-lg border border-info-100 bg-info-50 px-4 py-3 flex items-start gap-2">
        <Info className="w-4 h-4 text-info-600 mt-0.5 shrink-0" />
        <p className="text-sm text-info-700"><strong>Simulation only</strong> — no Salary Rules or payroll records will be changed.</p>
      </div>

      {error && <div className="text-sm text-danger-700 bg-danger-50 border border-danger-100 p-3 rounded-md">{error}</div>}

      <SectionCard>
        <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">1. Scope</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="sm:col-span-1">
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Salary Structure</label>
            <SearchableSelect
              value={structureId}
              onChange={setStructureId}
              options={structures.map(s => ({ id: s.id, label: s.name }))}
              placeholder="Select structure"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Period Start</label>
            <input type="date" value={periodStart} onChange={e => setPeriodStart(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Period End</label>
            <input type="date" value={periodEnd} onChange={e => setPeriodEnd(e.target.value)} className={inputClass} />
          </div>
        </div>
        <div className="mt-4">
          <Button variant="secondary" size="sm" loading={loadingCandidates} disabled={!structureId || !periodStart || !periodEnd} onClick={loadEligible}>
            Load Eligible Employees <ArrowRight className="w-3.5 h-3.5" />
          </Button>
        </div>

        {candidates.length > 0 && (
          <div className="mt-4 border-t border-gray-100 pt-4 max-h-64 overflow-y-auto space-y-1">
            {candidates.map(c => (
              <label key={c.employee.id} className={`flex items-center gap-2.5 px-2 py-1.5 rounded-md text-sm ${c.eligible ? 'cursor-pointer hover:bg-gray-50' : 'opacity-50'}`}>
                <input type="checkbox" disabled={!c.eligible} checked={selected.has(c.employee.id)} onChange={() => toggle(c.employee.id)}
                  className="rounded border-gray-300 text-brand-600 focus:ring-brand-500" />
                <span className="flex-1">{c.employee.first_name} {c.employee.last_name}</span>
                {!c.eligible && <span className="text-xs text-gray-400">{c.reason}</span>}
              </label>
            ))}
          </div>
        )}
      </SectionCard>

      {structureDetail && (
        <SectionCard>
          <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">2. Scenario</p>
          <div className="space-y-2">
            {structureDetail.rules.filter(r => r.is_active).sort((a, b) => a.sequence - b.sequence).map((rule, i, arr) => (
              <RuleRow
                key={rule.id}
                rule={rule}
                draft={overrides.get(rule.id) ?? null}
                earlierCodes={arr.slice(0, i).map(r => r.code)}
                onChange={(d) => setOverrides(prev => {
                  const next = new Map(prev);
                  if (d === null) next.delete(rule.id); else next.set(rule.id, d);
                  return next;
                })}
              />
            ))}
          </div>

          <div className="mt-4 pt-4 border-t border-gray-100 flex items-center gap-2">
            <Button variant="primary" size="sm" loading={running} disabled={selected.size === 0} onClick={runSimulation}>
              <FlaskConical className="w-3.5 h-3.5" /> Run Simulation
            </Button>
            <Button variant="secondary" size="sm" disabled={overrides.size === 0} onClick={resetScenario}>
              <RotateCcw className="w-3.5 h-3.5" /> Reset Scenario
            </Button>
            <Button variant="ghost" size="sm" onClick={discard}>
              <Trash2 className="w-3.5 h-3.5" /> Discard
            </Button>
          </div>
        </SectionCard>
      )}

      {result && (
        <>
          <SectionCard>
            <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Impact Summary</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-gray-400">Total Net (current → simulated)</p>
                <p className="text-lg font-bold text-gray-900 font-mono">{formatMoney(result.aggregate.current_total_net)} → {formatMoney(result.aggregate.simulated_total_net)}</p>
                <p className={`text-xs font-mono ${parseFloat(result.aggregate.delta_net) > 0 ? 'text-brand-700' : parseFloat(result.aggregate.delta_net) < 0 ? 'text-danger-600' : 'text-gray-400'}`}>
                  {parseFloat(result.aggregate.delta_net) >= 0 ? '+' : ''}{formatMoney(result.aggregate.delta_net)} this period
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Total Gross</p>
                <p className="text-sm font-semibold text-gray-900 font-mono">{formatMoney(result.aggregate.current_total_gross)} → {formatMoney(result.aggregate.simulated_total_gross)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Total Deductions</p>
                <p className="text-sm font-semibold text-gray-900 font-mono">{formatMoney(result.aggregate.current_total_deductions)} → {formatMoney(result.aggregate.simulated_total_deductions)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Employees</p>
                <p className="text-sm text-gray-700">{result.aggregate.employees_increased} up · {result.aggregate.employees_decreased} down · {result.aggregate.employees_unchanged} unchanged</p>
              </div>
              {result.employees_excluded > 0 && (
                <div>
                  <p className="text-xs text-gray-400">Excluded</p>
                  <p className="text-sm text-warning-700">{result.employees_excluded} of {result.employees_selected} — see reasons below</p>
                </div>
              )}
              {result.aggregate.annualized_net_delta_estimate != null && (
                <div>
                  <p className="text-xs text-gray-400">Annualized estimate</p>
                  <p className="text-sm font-semibold text-gray-900 font-mono">{formatMoney(result.aggregate.annualized_net_delta_estimate)}</p>
                  <p className="text-[11px] text-gray-400">assuming this monthly scenario recurs — not a forecast</p>
                </div>
              )}
            </div>
          </SectionCard>

          <SectionCard padded={false}>
            <div className="px-6 py-4 border-b border-gray-100">
              <h2 className="text-sm font-semibold text-gray-900">Employee Impact</h2>
            </div>
            {result.employees.length === 0 ? (
              <EmptyState icon={FlaskConical} title="No employees simulated" description="Everyone selected was excluded — see reasons above." />
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Employee</th>
                    <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Department</th>
                    <th className="px-6 py-2.5 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Current Net</th>
                    <th className="px-6 py-2.5 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Simulated Net</th>
                    <th className="px-6 py-2.5 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Δ</th>
                    <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {result.employees.map(r => {
                    const Icon = STATUS_ICON[r.status];
                    return (
                      <Fragment key={r.employee_id}>
                        <tr
                          className={r.excluded ? '' : 'cursor-pointer hover:bg-gray-50'}
                          onClick={() => !r.excluded && setInspecting(inspecting === r.employee_id ? null : r.employee_id)}
                        >
                          <td className="px-6 py-3 text-sm font-medium text-gray-900">{r.employee_name}</td>
                          <td className="px-6 py-3 text-sm text-gray-500">{r.department ?? '—'}</td>
                          <td className="px-6 py-3 text-sm text-right font-mono text-gray-700">{r.current ? formatMoney(r.current.net) : '—'}</td>
                          <td className="px-6 py-3 text-sm text-right font-mono text-gray-900">{r.simulated ? formatMoney(r.simulated.net) : '—'}</td>
                          <td className="px-6 py-3 text-sm text-right font-mono">
                            {r.delta_net != null ? (
                              <span className={parseFloat(r.delta_net) > 0 ? 'text-brand-700' : parseFloat(r.delta_net) < 0 ? 'text-danger-600' : 'text-gray-400'}>
                                {parseFloat(r.delta_net) >= 0 ? '+' : ''}{formatMoney(r.delta_net)}
                              </span>
                            ) : '—'}
                          </td>
                          <td className="px-6 py-3">
                            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[r.status]}`}>
                              <Icon className="w-3 h-3" /> {r.excluded ? (r.exclusion_reason ?? 'Excluded') : r.status}
                            </span>
                          </td>
                        </tr>
                        {inspecting === r.employee_id && !r.excluded && (
                          <tr><td colSpan={6}><EmployeeInspector result={r} onClose={() => setInspecting(null)} /></td></tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            )}
          </SectionCard>
        </>
      )}
    </div>
  );
}
