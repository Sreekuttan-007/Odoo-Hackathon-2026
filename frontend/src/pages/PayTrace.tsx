import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import type { PayTrace as PayTraceData, PayTraceEntry, PayTraceNarration } from '../types';
import { SectionCard } from '../components/ui/SectionCard';
import { Button } from '../components/ui/Button';
import { Skeleton } from '../components/ui/Skeleton';
import { formatDate, formatMoney } from '../lib/format';
import {
  ArrowLeft, Sparkles, ChevronDown, ArrowDown, AlertTriangle,
  Percent, Hash, FunctionSquare,
} from 'lucide-react';

const CATEGORY_STYLE: Record<string, string> = {
  BASIC: 'bg-gray-100 text-gray-600',
  ALLOWANCE: 'bg-brand-50 text-brand-700',
  GROSS: 'bg-info-50 text-info-700',
  DEDUCTION: 'bg-danger-50 text-danger-700',
  NET: 'bg-brand-600 text-white',
};

const METHOD_ICON: Record<string, typeof Percent> = {
  FIXED: Hash,
  PERCENTAGE: Percent,
  FORMULA: FunctionSquare,
};

function TraceRow({ entry, onDependencyHover }: { entry: PayTraceEntry; onDependencyHover: (code: string | null) => void }) {
  const [expanded, setExpanded] = useState(false);
  const MethodIcon = METHOD_ICON[entry.method] ?? Hash;
  const isNet = entry.category === 'NET';
  const isDeduction = entry.category === 'DEDUCTION';

  return (
    <div
      id={`trace-${entry.rule_code}`}
      className={`relative rounded-lg border transition-colors ${isNet ? 'border-brand-200 bg-brand-50/40' : 'border-gray-100 bg-white'}`}
      onMouseEnter={() => entry.depends_on.length && onDependencyHover(entry.rule_code)}
      onMouseLeave={() => onDependencyHover(null)}
    >
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-start gap-3 px-4 py-3 text-left"
      >
        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gray-900 text-white text-[10px] font-mono font-semibold">
          {String(entry.sequence).padStart(2, '0')}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-gray-900">{entry.rule_name}</span>
            <span className="font-mono text-[11px] text-gray-400">{entry.rule_code}</span>
            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${CATEGORY_STYLE[entry.category] ?? 'bg-gray-100 text-gray-600'}`}>
              {entry.category}
            </span>
            {!entry.has_structured_history && (
              <span className="inline-flex items-center gap-1 text-[10px] text-gray-400">
                <AlertTriangle className="w-3 h-3" /> legacy
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-600">{entry.explanation}</p>
          {entry.depends_on.length > 0 && (
            <p className="mt-1 text-xs text-gray-400">
              depends on{' '}
              {entry.depends_on.map((code, i) => (
                <span key={code}>
                  <span className="font-mono text-gray-500">{code}</span>{i < entry.depends_on.length - 1 ? ', ' : ''}
                </span>
              ))}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2 pl-2">
          <span className={`font-mono text-sm font-semibold ${isDeduction ? 'text-danger-600' : 'text-gray-900'}`}>
            {isDeduction ? '−' : ''}{formatMoney(entry.result)}
          </span>
          <ChevronDown className={`w-3.5 h-3.5 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {expanded && (
        <div className="animate-load-in border-t border-gray-100 px-4 py-3 ml-9">
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs sm:grid-cols-3">
            <div><span className="text-gray-400">Method</span><p className="flex items-center gap-1 mt-0.5 font-medium text-gray-700"><MethodIcon className="w-3 h-3" /> {entry.method}</p></div>
            <div><span className="text-gray-400">Sequence</span><p className="mt-0.5 font-mono font-medium text-gray-700">{entry.sequence}</p></div>
            {entry.quantity && entry.quantity !== '1.00' && (
              <div><span className="text-gray-400">Quantity</span><p className="mt-0.5 font-medium text-gray-700">{entry.quantity}</p></div>
            )}
          </div>
          {entry.calculation?.formula && (
            <div className="mt-3">
              <span className="text-xs text-gray-400">Formula</span>
              <pre className="mt-1 whitespace-pre-wrap rounded-md bg-gray-50 px-3 py-2 font-mono text-xs text-gray-700">{entry.calculation.formula}</pre>
              {entry.calculation.inputs && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {Object.entries(entry.calculation.inputs).map(([code, value]) => (
                    <span key={code} className="rounded-md bg-gray-50 px-2 py-1 font-mono text-[11px] text-gray-600">
                      {code} = ₹{value}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
          {!entry.has_structured_history && (
            <p className="mt-2 text-xs text-gray-400 italic">
              This payslip was computed before detailed calculation history was tracked — only the summary above is available.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export function PayTrace() {
  const { payslipId } = useParams();
  const navigate = useNavigate();

  const [trace, setTrace] = useState<PayTraceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);

  const [narration, setNarration] = useState<PayTraceNarration | null>(null);
  const [narrating, setNarrating] = useState(false);
  const [narrationError, setNarrationError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    api.get(`/payroll/payslips/${payslipId}/trace`)
      .then(res => setTrace(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [payslipId]);

  const explainInSimpleLanguage = async () => {
    setNarrating(true);
    setNarrationError(false);
    try {
      const res = await api.get(`/payroll/payslips/${payslipId}/trace/explain`, { params: { mode: 'employee' } });
      setNarration(res.data);
      if (!res.data.available) setNarrationError(true);
    } catch {
      setNarrationError(true);
    } finally {
      setNarrating(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-3xl space-y-4">
        <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
        <Skeleton className="h-32 w-full rounded-2xl" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    );
  }

  if (error || !trace) {
    return (
      <div className="text-center py-16">
        <h2 className="text-base font-semibold text-gray-800">PayTrace unavailable</h2>
        <Button variant="ghost" className="mt-4" onClick={() => navigate(-1)}>← Back</Button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-5">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Payslip
      </button>

      <div>
        <p className="eyebrow mb-2">PayTrace</p>
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Every rupee, explained.</h1>
        <p className="text-sm text-gray-500 mt-1">
          A deterministic, verified record of how this Payslip's Net Pay was calculated — never regenerated from current Salary Rules, only from what actually ran.
        </p>
      </div>

      {!trace.available ? (
        <SectionCard>
          <div className="text-center py-8">
            <h2 className="text-sm font-semibold text-gray-800">{trace.reason === 'NOT_COMPUTED' ? 'Payroll has not been computed yet' : 'No calculation to trace'}</h2>
            <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">{trace.message}</p>
          </div>
        </SectionCard>
      ) : (
        <>
          <SectionCard>
            <div className="flex items-start justify-between flex-wrap gap-3">
              <div>
                <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">{trace.employee.name}</p>
                <p className="text-sm text-gray-500 mt-0.5">
                  {trace.salary_structure.name} · {formatDate(trace.period.start)} — {formatDate(trace.period.end)}
                </p>
                {trace.contract && (
                  <p className="text-xs text-gray-400 mt-1">Contract {trace.contract.reference} · {formatMoney(trace.contract.wage_monthly)} / month</p>
                )}
              </div>
              <div className="text-right">
                <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Net Pay</p>
                <p className="text-2xl font-bold text-brand-700 font-mono">{formatMoney(trace.aggregates.net)}</p>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-gray-100">
              <Button variant="secondary" size="sm" loading={narrating} onClick={explainInSimpleLanguage}>
                <Sparkles className="w-3.5 h-3.5" /> Explain in Simple Language
              </Button>

              {narration && narration.available && (
                <div className="animate-load-in mt-3 rounded-lg bg-info-50 border border-info-100 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-info-600 mb-1">Plain-language summary</p>
                  <p className="text-sm text-info-800">{narration.summary}</p>
                  <p className="text-[11px] text-info-500 mt-2 italic">Generated from the verified PayTrace calculation below — it cannot change any number.</p>
                </div>
              )}
              {narrationError && (
                <div className="animate-load-in mt-3 rounded-lg bg-gray-50 border border-gray-200 px-4 py-3">
                  <p className="text-sm text-gray-600">Plain-language explanation is temporarily unavailable.</p>
                  <p className="text-xs text-gray-400 mt-1">The verified calculation trace below is complete regardless.</p>
                </div>
              )}
            </div>
          </SectionCard>

          {trace.contract && (
            <div className="flex items-center justify-center">
              <div className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-center">
                <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wide">Contract Wage</p>
                <p className="font-mono text-sm font-semibold text-gray-900">{formatMoney(trace.contract.wage_monthly)}</p>
              </div>
            </div>
          )}
          {trace.contract && (
            <div className="flex justify-center"><ArrowDown className="w-4 h-4 text-gray-300" /></div>
          )}

          <div className="space-y-2">
            {(() => {
              const hoveredDeps = new Set(trace.entries.find(e => e.rule_code === hovered)?.depends_on ?? []);
              return trace.entries.map((entry, i) => (
                <div key={entry.rule_code}>
                  <div className={`rounded-lg transition-shadow ${hoveredDeps.has(entry.rule_code) ? 'ring-2 ring-brand-300' : ''}`}>
                    <TraceRow entry={entry} onDependencyHover={setHovered} />
                  </div>
                  {i < trace.entries.length - 1 && (
                    <div className="flex justify-center py-1"><ArrowDown className="w-3.5 h-3.5 text-gray-300" /></div>
                  )}
                </div>
              ));
            })()}
          </div>

          <SectionCard>
            <h2 className="text-sm font-semibold text-gray-900 mb-3">Gross → Net breakdown</h2>
            <div className="space-y-1.5">
              {trace.aggregates.gross_components.map(c => (
                <div key={c.rule_code} className="flex justify-between text-sm"><span className="text-gray-600">{c.rule_name}</span><span className="font-mono text-gray-900">{formatMoney(c.amount)}</span></div>
              ))}
              <div className="flex justify-between text-sm font-semibold border-t border-gray-100 pt-1.5"><span className="text-gray-700">Gross</span><span className="font-mono text-gray-900">{formatMoney(trace.aggregates.gross)}</span></div>
              {trace.aggregates.net_components.filter(c => c.rule_code !== 'GROSS').map(c => (
                <div key={c.rule_code} className="flex justify-between text-sm"><span className="text-gray-600">{c.rule_name}</span><span className="font-mono text-danger-600">−{formatMoney(c.amount)}</span></div>
              ))}
              <div className="flex justify-between text-base font-bold border-t-2 border-gray-200 pt-2 mt-1"><span className="text-gray-900">Net Pay</span><span className="font-mono text-brand-700">{formatMoney(trace.aggregates.net)}</span></div>
            </div>
          </SectionCard>

          <p className="text-center text-xs text-gray-400 pb-4">
            Payloom does not use AI to calculate or reconstruct these numbers — this is the actual historical execution trace.{' '}
            <Link to={`/payroll/payslips/${payslipId}`} className="text-brand-600 hover:text-brand-700 font-medium">Back to Payslip</Link>
          </p>
        </>
      )}
    </div>
  );
}
