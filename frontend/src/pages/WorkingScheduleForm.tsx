import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { DAYS_OF_WEEK } from '../types';
import type { DayOfWeek, ScheduleStatus } from '../types';
import { useToast, ToastViewport } from '../components/Toast';
import { SectionCard } from '../components/ui/SectionCard';
import { Button } from '../components/ui/Button';
import { Skeleton } from '../components/ui/Skeleton';
import { ArrowLeft, Copy, Clock } from 'lucide-react';

interface Row {
  enabled: boolean;
  start: string;
  end: string;
  breakMinutes: number;
}

const DAY_LABELS: Record<DayOfWeek, string> = {
  MONDAY: 'Monday', TUESDAY: 'Tuesday', WEDNESDAY: 'Wednesday', THURSDAY: 'Thursday',
  FRIDAY: 'Friday', SATURDAY: 'Saturday', SUNDAY: 'Sunday',
};

const DEFAULT_ROW: Row = { enabled: false, start: '09:00', end: '18:00', breakMinutes: 60 };
const inputClass = 'h-9 px-3 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500';

function toMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number);
  return h * 60 + m;
}

function rowHours(row: Row): { hours: number; error: string | null } {
  if (!row.enabled) return { hours: 0, error: null };
  const duration = toMinutes(row.end) - toMinutes(row.start);
  if (duration <= 0) return { hours: 0, error: 'End time must be after start time.' };
  const worked = duration - row.breakMinutes;
  if (worked < 0) return { hours: 0, error: 'Break exceeds shift duration.' };
  return { hours: Math.round((worked / 60) * 100) / 100, error: null };
}

export function WorkingScheduleForm() {
  const { scheduleId } = useParams();
  const navigate = useNavigate();
  const { toasts, push } = useToast();
  const isEdit = !!scheduleId;

  const [name, setName] = useState('');
  const [company, setCompany] = useState('Payloom Inc.');
  const [timezone, setTimezone] = useState('Asia/Kolkata');
  const [status, setStatus] = useState<ScheduleStatus>('ACTIVE');
  const [rows, setRows] = useState<Record<DayOfWeek, Row>>(() => {
    const init = {} as Record<DayOfWeek, Row>;
    DAYS_OF_WEEK.forEach(d => { init[d] = { ...DEFAULT_ROW }; });
    return init;
  });
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isEdit) return;
    api.get(`/working-schedules/${scheduleId}`).then(res => {
      const s = res.data;
      setName(s.name);
      setCompany(s.company);
      setTimezone(s.timezone);
      setStatus(s.status);
      const init = {} as Record<DayOfWeek, Row>;
      DAYS_OF_WEEK.forEach(d => { init[d] = { ...DEFAULT_ROW, enabled: false }; });
      for (const line of s.lines) {
        init[line.day_of_week as DayOfWeek] = {
          enabled: true,
          start: line.start_time.slice(0, 5),
          end: line.end_time.slice(0, 5),
          breakMinutes: line.break_minutes,
        };
      }
      setRows(init);
    }).finally(() => setLoading(false));
  }, [isEdit, scheduleId]);

  const updateRow = (day: DayOfWeek, patch: Partial<Row>) => {
    setRows(r => ({ ...r, [day]: { ...r[day], ...patch } }));
  };

  const copyMondayToWeekdays = () => {
    const monday = rows.MONDAY;
    setRows(r => ({
      ...r,
      TUESDAY: { ...monday }, WEDNESDAY: { ...monday }, THURSDAY: { ...monday }, FRIDAY: { ...monday },
    }));
  };

  const computed = DAYS_OF_WEEK.map(day => ({ day, ...rowHours(rows[day]) }));
  const daysPerWeek = computed.filter(c => rows[c.day].enabled).length;
  const hoursPerWeek = Math.round(computed.reduce((sum, c) => sum + c.hours, 0) * 100) / 100;
  const hasErrors = computed.some(c => rows[c.day].enabled && c.error);

  const handleSave = async () => {
    setSaving(true);
    try {
      const lines = DAYS_OF_WEEK
        .filter(d => rows[d].enabled)
        .map(d => ({
          day_of_week: d,
          start_time: `${rows[d].start}:00`,
          end_time: `${rows[d].end}:00`,
          break_minutes: rows[d].breakMinutes,
        }));
      const payload = { name, company, timezone, status, lines };
      if (isEdit) {
        await api.patch(`/working-schedules/${scheduleId}`, payload);
        push('Schedule saved.');
      } else {
        const res = await api.post('/working-schedules', payload);
        push('Schedule created.');
        navigate(`/working-schedules/${res.data.id}`, { replace: true });
        return;
      }
    } catch (err: any) {
      push(err.response?.data?.detail?.error?.message || 'Failed to save schedule.', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-5 max-w-4xl">
        <div className="h-4 w-40 bg-gray-100 rounded animate-pulse" />
        <SectionCard>
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-11 w-full" />)}
          </div>
        </SectionCard>
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-4xl">
      <button onClick={() => navigate('/working-schedules')} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Working Schedules
      </button>

      <SectionCard className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Schedule Name</label>
            <input required value={name} onChange={e => setName(e.target.value)} placeholder="40 Hours / Week" className={`w-full ${inputClass}`} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Company</label>
            <input value={company} onChange={e => setCompany(e.target.value)} className={`w-full ${inputClass}`} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Timezone</label>
            <input value={timezone} onChange={e => setTimezone(e.target.value)} className={`w-full ${inputClass}`} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1.5">Status</label>
            <select value={status} onChange={e => setStatus(e.target.value as ScheduleStatus)} className={`w-full ${inputClass}`}>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
            </select>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-900">Weekly Pattern</h3>
            <button type="button" onClick={copyMondayToWeekdays} className="inline-flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-700 transition-colors">
              <Copy className="w-3.5 h-3.5" /> Copy Monday to weekdays
            </button>
          </div>

          <div className="space-y-2">
            {DAYS_OF_WEEK.map(day => {
              const row = rows[day];
              const { hours, error } = rowHours(row);
              return (
                <div key={day} className={`flex flex-wrap items-center gap-3 rounded-lg border px-3.5 py-2.5 transition-colors ${row.enabled ? (error ? 'border-danger-200 bg-danger-50/50' : 'border-gray-200') : 'border-gray-100 bg-gray-50/50'}`}>
                  <label className="flex items-center gap-2 w-28 shrink-0">
                    <input type="checkbox" checked={row.enabled} onChange={e => updateRow(day, { enabled: e.target.checked })}
                      className="rounded border-gray-300 text-brand-600 focus:ring-brand-500" />
                    <span className={`text-sm font-medium ${row.enabled ? 'text-gray-900' : 'text-gray-400'}`}>{DAY_LABELS[day]}</span>
                  </label>

                  {row.enabled && (
                    <>
                      <input type="time" value={row.start} onChange={e => updateRow(day, { start: e.target.value })} className={inputClass} />
                      <span className="text-gray-400 text-sm">to</span>
                      <input type="time" value={row.end} onChange={e => updateRow(day, { end: e.target.value })} className={inputClass} />
                      <div className="flex items-center gap-1.5">
                        <input type="number" min={0} value={row.breakMinutes} onChange={e => updateRow(day, { breakMinutes: parseInt(e.target.value) || 0 })}
                          className={`w-20 ${inputClass}`} />
                        <span className="text-xs text-gray-400">min break</span>
                      </div>
                      <div className="ml-auto flex items-center gap-1.5 text-sm font-semibold">
                        <Clock className="w-3.5 h-3.5 text-gray-400" />
                        {error ? <span className="text-danger-600 text-xs font-normal">{error}</span> : <span className="text-gray-900">{hours}h</span>}
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="flex items-center justify-between rounded-lg bg-brand-50 border border-brand-100 px-4 py-3">
          <span className="text-sm font-medium text-brand-900">Weekly Summary</span>
          <span className="text-sm font-semibold text-brand-900">{daysPerWeek} days / week · {hoursPerWeek}h / week</span>
        </div>

        <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
          <Button variant="secondary" onClick={() => navigate('/working-schedules')}>Cancel</Button>
          <Button variant="primary" loading={saving} disabled={!name || hasErrors} onClick={handleSave}>
            {isEdit ? 'Save Changes' : 'Create Schedule'}
          </Button>
        </div>
      </SectionCard>
      <ToastViewport toasts={toasts} />
    </div>
  );
}
