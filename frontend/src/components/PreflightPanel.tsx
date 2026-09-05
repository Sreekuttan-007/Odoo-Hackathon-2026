import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { PreflightResult, PreflightFinding, PreflightReadiness, WarningSeverity } from '../types';
import { Button } from './ui/Button';
import { SectionCard } from './ui/SectionCard';
import {
  ShieldCheck, ShieldAlert, ShieldQuestion, RefreshCw, ChevronDown,
  AlertOctagon, AlertTriangle, Info, ArrowRight,
} from 'lucide-react';

const READINESS: Record<PreflightReadiness, { label: string; tone: string; dot: string; icon: typeof ShieldCheck; blurb: string }> = {
  NOT_RUN: {
    label: 'Not run', tone: 'bg-gray-100 text-gray-600', dot: 'bg-gray-400', icon: ShieldQuestion,
    blurb: 'Compute this Payrun to run Preflight.',
  },
  ACTION_REQUIRED: {
    label: 'Action required', tone: 'bg-danger-50 text-danger-700', dot: 'bg-danger-500', icon: ShieldAlert,
    blurb: 'Resolve the blockers below before this payroll can be validated.',
  },
  REVIEW_RECOMMENDED: {
    label: 'Review recommended', tone: 'bg-warning-50 text-warning-700', dot: 'bg-warning-500', icon: ShieldQuestion,
    blurb: 'No blockers — but some items should be reviewed before payment.',
  },
  READY: {
    label: 'Ready to validate', tone: 'bg-brand-50 text-brand-700', dot: 'bg-brand-500', icon: ShieldCheck,
    blurb: 'No blocking payroll issues were detected.',
  },
};

const SEVERITY: Record<WarningSeverity, { label: string; chip: string; icon: typeof Info; order: number }> = {
  BLOCKER: { label: 'Blocker', chip: 'bg-danger-50 text-danger-700', icon: AlertOctagon, order: 0 },
  WARNING: { label: 'Warning', chip: 'bg-warning-50 text-warning-700', icon: AlertTriangle, order: 1 },
  INFO: { label: 'Info', chip: 'bg-info-50 text-info-700', icon: Info, order: 2 },
};

type Filter = 'ALL' | WarningSeverity;

function findingActions(f: PreflightFinding): { label: string; to: string }[] {
  const actions: { label: string; to: string }[] = [];
  const contractCodes = ['MISSING_APPLICABLE_CONTRACT', 'CONTRACT_CONFLICT', 'CONTRACT_STARTS_MID_PERIOD', 'CONTRACT_ENDS_MID_PERIOD'];
  const attendanceCodes = ['INCOMPLETE_ATTENDANCE', 'LONG_ATTENDANCE_SESSION', 'ATTENDANCE_ABOVE_SCHEDULE'];

  if (contractCodes.includes(f.code) && f.employee_id) {
    actions.push({ label: 'View employee', to: `/employees/${f.employee_id}` });
    actions.push({ label: 'View contracts', to: `/contracts?employee_id=${f.employee_id}` });
  }
  if (attendanceCodes.includes(f.code) && f.employee_id) {
    actions.push({ label: 'View attendance', to: `/attendance?employee_id=${f.employee_id}` });
  }
  if (f.payslip_id) {
    actions.push({ label: 'Inspect payslip', to: `/payroll/payslips/${f.payslip_id}` });
    if (['LARGE_NET_VARIANCE', 'DEDUCTIONS_EXCEED_GROSS', 'NEGATIVE_NET_PAY'].includes(f.code)) {
      actions.push({ label: 'Explain salary', to: `/payroll/payslips/${f.payslip_id}/trace` });
    }
  }
  return actions;
}

function EvidenceBlock({ evidence }: { evidence: Record<string, unknown> }) {
  const entries = Object.entries(evidence).filter(([k]) => k !== 'origin' && k !== 'note');
  if (entries.length === 0) return null;
  return (
    <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-2">
      {entries.map(([key, value]) => (
        <div key={key} className="flex justify-between gap-3 text-xs">
          <dt className="text-gray-400 capitalize">{key.replace(/_/g, ' ')}</dt>
          <dd className="font-mono text-gray-700 text-right break-all">
            {typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function FindingRow({ finding }: { finding: PreflightFinding }) {
  const [open, setOpen] = useState(false);
  const sev = SEVERITY[finding.severity];
  const SevIcon = sev.icon;
  const actions = findingActions(finding);
  const note = typeof finding.evidence?.note === 'string' ? finding.evidence.note : null;

  return (
    <div className="rounded-lg border border-gray-100 bg-white">
      <button onClick={() => setOpen(o => !o)} className="flex w-full items-start gap-3 px-3.5 py-3 text-left">
        <SevIcon className={`mt-0.5 h-4 w-4 shrink-0 ${finding.severity === 'BLOCKER' ? 'text-danger-500' : finding.severity === 'WARNING' ? 'text-warning-500' : 'text-info-500'}`} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${sev.chip}`}>{sev.label}</span>
            {finding.employee_name && <span className="text-xs font-medium text-gray-500">{finding.employee_name}</span>}
            <span className="font-mono text-[10px] text-gray-300">{finding.code}</span>
          </div>
          <p className="mt-1 text-sm text-gray-800">{finding.message}</p>
        </div>
        <ChevronDown className={`mt-0.5 h-3.5 w-3.5 shrink-0 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="animate-load-in border-t border-gray-100 px-3.5 py-3 pl-10">
          <EvidenceBlock evidence={finding.evidence} />
          {note && <p className="mt-2 text-xs italic text-gray-400">{note}</p>}
          {finding.resolution && (
            <p className="mt-2 text-xs text-gray-600"><span className="font-medium text-gray-700">Resolution: </span>{finding.resolution}</p>
          )}
          {actions.length > 0 && (
            <div className="mt-2.5 flex flex-wrap gap-2">
              {actions.map(a => (
                <Link key={a.to + a.label} to={a.to} className="inline-flex items-center gap-1 rounded-md border border-gray-200 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900">
                  {a.label} <ArrowRight className="h-3 w-3" />
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Count({ n, label, tone }: { n: number; label: string; tone: string }) {
  return (
    <div className="text-center">
      <p className={`text-2xl font-bold tabular-nums ${n > 0 ? tone : 'text-gray-300'}`}>{n}</p>
      <p className="text-[11px] font-medium uppercase tracking-wide text-gray-400">{label}</p>
    </div>
  );
}

interface Props {
  result: PreflightResult | null;
  loading: boolean;
  onRun: () => void;
  panelId?: string;
}

export function PreflightPanel({ result, loading, onRun, panelId }: Props) {
  const [filter, setFilter] = useState<Filter>('ALL');

  const visible = useMemo(() => {
    if (!result) return [];
    const list = filter === 'ALL' ? result.findings : result.findings.filter(f => f.severity === filter);
    return [...list].sort((a, b) => SEVERITY[a.severity].order - SEVERITY[b.severity].order);
  }, [result, filter]);

  if (!result) {
    return (
      <SectionCard>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          {loading ? 'Checking payroll…' : 'Preflight not available.'}
        </div>
      </SectionCard>
    );
  }

  const r = READINESS[result.readiness];
  const RIcon = r.icon;
  const { blockers, warnings, info } = result.summary;
  const notRun = result.readiness === 'NOT_RUN';

  return (
    <SectionCard>
      <div id={panelId} className="scroll-mt-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">Payroll Preflight</h2>
            <p className="mt-0.5 text-xs text-gray-400">
              Deterministic readiness &amp; risk checks · {result.reference}
            </p>
          </div>
          <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${r.tone}`}>
            <RIcon className="h-3.5 w-3.5" /> {r.label}
          </span>
        </div>

        {notRun ? (
          <p className="mt-4 text-sm text-gray-500">{result.message || r.blurb}</p>
        ) : (
          <>
            <div className="mt-4 grid grid-cols-3 gap-4 rounded-lg border border-gray-100 bg-gray-50/60 p-4">
              <Count n={blockers} label="Blockers" tone="text-danger-600" />
              <Count n={warnings} label="Warnings" tone="text-warning-600" />
              <Count n={info} label="Info" tone="text-info-600" />
            </div>

            <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-gray-600">{r.blurb}</p>
              <Button variant="secondary" size="sm" loading={loading} onClick={onRun}>
                <RefreshCw className="h-3.5 w-3.5" /> Run again
              </Button>
            </div>

            {result.findings.length > 0 && (
              <>
                <div className="mt-4 flex gap-1.5 border-b border-gray-100">
                  {(['ALL', 'BLOCKER', 'WARNING', 'INFO'] as Filter[]).map(f => {
                    const count = f === 'ALL' ? result.findings.length : result.summary[f === 'BLOCKER' ? 'blockers' : f === 'WARNING' ? 'warnings' : 'info'];
                    return (
                      <button
                        key={f}
                        onClick={() => setFilter(f)}
                        className={`-mb-px border-b-2 px-2.5 py-1.5 text-xs font-medium transition-colors ${filter === f ? 'border-brand-600 text-brand-700' : 'border-transparent text-gray-400 hover:text-gray-600'}`}
                      >
                        {f === 'ALL' ? 'All' : SEVERITY[f as WarningSeverity].label + 's'} ({count})
                      </button>
                    );
                  })}
                </div>
                <div className="mt-3 space-y-2">
                  {visible.length === 0
                    ? <p className="py-4 text-center text-sm text-gray-400">Nothing in this category.</p>
                    : visible.map((f, i) => <FindingRow key={f.code + f.payslip_id + i} finding={f} />)}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </SectionCard>
  );
}
