import { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import type { PayrollBrief as Brief, BriefItem, WarningSeverity } from '../types';
import { Button } from './ui/Button';
import { SectionCard } from './ui/SectionCard';
import {
  Sparkles, RefreshCw, AlertOctagon, AlertTriangle, Info, ArrowRight, ListOrdered,
} from 'lucide-react';

const REASON_COPY: Record<string, string> = {
  NOT_CONFIGURED: 'the AI narrator is not configured on this environment',
  TIMEOUT: 'the AI provider took too long to respond',
  PROVIDER_ERROR: 'the AI provider returned an error',
  RATE_LIMITED: 'the AI provider is rate-limiting requests right now',
  MALFORMED_RESPONSE: 'the AI provider returned an unreadable response',
  NOT_COMPUTED: 'Compute this Payrun before generating a payroll brief.',
};

const SEVERITY: Record<WarningSeverity, { chip: string; icon: typeof Info }> = {
  BLOCKER: { chip: 'bg-danger-50 text-danger-700', icon: AlertOctagon },
  WARNING: { chip: 'bg-warning-50 text-warning-700', icon: AlertTriangle },
  INFO: { chip: 'bg-info-50 text-info-700', icon: Info },
};

const DISCLOSURE =
  'AI-generated explanation based only on verified Payloom payroll data. ' +
  'Payroll calculations are deterministic and are not performed by AI.';

const TITLE_CASE: Record<string, string> = { PAYROLL: 'Payroll', PREFLIGHT: 'Preflight', SIMULATOR: 'Simulator' };

function SourceLabel({ item }: { item: BriefItem }) {
  if (!item.source_type && !item.source_code) return null;
  const text = `Source: ${TITLE_CASE[item.source_type || ''] || item.source_type || ''}` +
    (item.source_code ? ` · ${item.source_code}` : '') +
    (item.source_ref ? ` · ${item.source_ref}` : '');
  const body = <span className="text-[11px] font-medium text-gray-400">{text}</span>;
  return item.route ? (
    <Link to={item.route} className="inline-flex items-center gap-1 hover:text-brand-600">
      {body} <ArrowRight className="h-3 w-3 text-gray-300" />
    </Link>
  ) : body;
}

function ItemRow({ item }: { item: BriefItem }) {
  const sev = item.priority ? SEVERITY[item.priority] : null;
  const SevIcon = sev?.icon ?? Info;
  return (
    <div className="rounded-lg border border-gray-100 bg-white px-3.5 py-3">
      <div className="flex items-start gap-3">
        <SevIcon className={`mt-0.5 h-4 w-4 shrink-0 ${item.priority === 'BLOCKER' ? 'text-danger-500' : item.priority === 'WARNING' ? 'text-warning-500' : 'text-gray-400'}`} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-gray-900">{item.title}</span>
            {item.priority && (
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${sev!.chip}`}>
                {item.priority}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-600">{item.text}</p>
          <div className="mt-1.5"><SourceLabel item={item} /></div>
        </div>
      </div>
    </div>
  );
}

interface Props {
  payrunId: string;
  canGenerate: boolean;
}

export function PayrollBrief({ payrunId, canGenerate }: Props) {
  const [brief, setBrief] = useState<Brief | null>(null);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    try {
      const res = await api.post(`/payroll/payruns/${payrunId}/intelligence/brief`, {});
      setBrief(res.data);
    } catch {
      setBrief(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SectionCard>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-gray-900">
            <Sparkles className="h-4 w-4 text-brand-500" /> Payloom Intelligence
          </h2>
          <p className="mt-0.5 text-xs text-gray-400">
            Grounded payroll brief · every statement traces back to a Payloom source
          </p>
        </div>
        {brief ? (
          <Button variant="secondary" size="sm" loading={loading} onClick={generate}>
            <RefreshCw className="h-3.5 w-3.5" /> Regenerate
          </Button>
        ) : (
          <Button variant="primary" size="sm" loading={loading} onClick={generate} disabled={!canGenerate}>
            <Sparkles className="h-3.5 w-3.5" /> Generate Payroll Brief
          </Button>
        )}
      </div>

      {loading && !brief && (
        <p className="mt-4 text-sm text-gray-500">
          Generating a grounded payroll brief from verified Payloom data…
        </p>
      )}

      {!loading && !brief && !canGenerate && (
        <p className="mt-4 text-sm text-gray-500">Compute this Payrun to generate a payroll brief.</p>
      )}

      {brief && (
        <div className="mt-4 animate-load-in space-y-5">
          {!brief.available && (
            <div className="rounded-lg border border-warning-100 bg-warning-50/60 px-3.5 py-3 text-sm text-warning-800">
              {brief.reason === 'NOT_COMPUTED'
                ? REASON_COPY.NOT_COMPUTED
                : `AI brief is temporarily unavailable — ${REASON_COPY[brief.reason || ''] || 'unknown error'}. ` +
                  'The verified summary below is generated deterministically by Payloom, not by AI.'}
            </div>
          )}

          {(brief.summary || brief.headline) && (
            <div>
              {brief.headline && <p className="text-sm font-semibold text-gray-900">{brief.headline}</p>}
              {brief.summary && <p className="mt-1 text-sm text-gray-600">{brief.summary}</p>}
              {brief.is_fallback && brief.available === false && brief.reason !== 'NOT_COMPUTED' && (
                <p className="mt-1 text-[11px] uppercase tracking-wide text-gray-400">Deterministic fallback · not AI-generated</p>
              )}
            </div>
          )}

          {brief.attention_items.length > 0 && (
            <div>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-gray-400">Needs attention</p>
              <div className="space-y-2">
                {brief.attention_items.map((it, i) => <ItemRow key={`a${i}`} item={it} />)}
              </div>
            </div>
          )}

          {brief.observations.length > 0 && (
            <div>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-gray-400">Observations</p>
              <div className="space-y-2">
                {brief.observations.map((it, i) => <ItemRow key={`o${i}`} item={it} />)}
              </div>
            </div>
          )}

          {brief.suggested_review_order.length > 0 && (
            <div>
              <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                <ListOrdered className="h-3.5 w-3.5" /> Suggested review order
              </p>
              <ol className="space-y-1.5">
                {brief.suggested_review_order.map((it, i) => (
                  <li key={`r${i}`} className="flex items-start gap-2 text-sm text-gray-600">
                    <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-gray-100 text-[10px] font-semibold text-gray-500">{i + 1}</span>
                    <span>{it.title}{it.text && it.title !== it.text ? ` — ${it.text}` : ''}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {brief.sources.length > 0 && (
            <details className="rounded-lg border border-gray-100 bg-gray-50/50 px-3.5 py-2.5">
              <summary className="cursor-pointer text-xs font-medium text-gray-500">
                Sources ({brief.sources.length})
              </summary>
              <ul className="mt-2 space-y-1.5">
                {brief.sources.map(s => (
                  <li key={s.id} className="flex items-start justify-between gap-3 text-xs">
                    <span className="text-gray-600">{s.label}</span>
                    <span className="shrink-0 font-mono text-[10px] text-gray-400">
                      {s.type} · {s.code}
                    </span>
                  </li>
                ))}
              </ul>
            </details>
          )}

          <p className="border-t border-gray-100 pt-3 text-[11px] leading-relaxed text-gray-400">
            {brief.available ? DISCLOSURE : 'This summary was generated deterministically by Payloom from verified payroll data. No AI was involved.'}
          </p>
        </div>
      )}
    </SectionCard>
  );
}
