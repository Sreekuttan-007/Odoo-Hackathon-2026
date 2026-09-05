import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { Attendance } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { SectionCard } from '../components/ui/SectionCard';
import { DetailField } from '../components/ui/DetailField';
import { SkeletonDetail } from '../components/ui/Skeleton';
import { Button } from '../components/ui/Button';
import { useToast, ToastViewport } from '../components/Toast';
import { formatDate, formatDateTime, formatMinutes } from '../lib/format';
import { ArrowLeft, LogIn, LogOut, Timer, StickyNote, Pencil, AlertTriangle } from 'lucide-react';

const HR_ROLES = ['HR_MANAGER', 'HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];

function toLocalInputValue(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function AttendanceDetail() {
  const { attendanceId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toasts, push } = useToast();
  const canCorrect = !!user && HR_ROLES.includes(user.role);

  const [record, setRecord] = useState<Attendance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [editing, setEditing] = useState(false);
  const [checkIn, setCheckIn] = useState('');
  const [checkOut, setCheckOut] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  const fetchRecord = () => {
    setLoading(true);
    setError(false);
    api.get(`/attendance/${attendanceId}`)
      .then(res => setRecord(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(fetchRecord, [attendanceId]);

  const startEditing = () => {
    if (!record) return;
    setCheckIn(toLocalInputValue(record.check_in));
    setCheckOut(record.check_out ? toLocalInputValue(record.check_out) : '');
    setNotes(record.notes || '');
    setFormError('');
    setEditing(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setFormError('');
    try {
      const payload: Record<string, unknown> = {
        check_in: new Date(checkIn).toISOString(),
        notes: notes || null,
      };
      if (checkOut) payload.check_out = new Date(checkOut).toISOString();
      const res = await api.patch(`/attendance/${attendanceId}`, payload);
      setRecord(res.data);
      setEditing(false);
      push('Attendance corrected.');
    } catch (err: any) {
      setFormError(err.response?.data?.detail?.error?.message || 'Failed to save correction.');
    } finally {
      setSaving(false);
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

  if (error || !record) {
    return (
      <div className="text-center py-16">
        <h2 className="text-base font-semibold text-gray-800">Attendance record not found</h2>
        <Button variant="ghost" className="mt-4" onClick={() => navigate('/attendance')}>← Back to Attendance</Button>
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
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Attendance</p>
            <h1 className="text-lg font-semibold text-gray-900 mt-0.5">{formatDate(record.attendance_date)}</h1>
            <Link to={`/employees/${record.employee.id}`} className="text-sm text-brand-600 hover:text-brand-700 font-medium">
              {record.employee.first_name} {record.employee.last_name}
            </Link>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={record.status} />
            {canCorrect && !editing && (
              <Button variant="secondary" size="sm" onClick={startEditing}>
                <Pencil className="w-3.5 h-3.5" /> Correct
              </Button>
            )}
          </div>
        </div>

        {record.status === 'MISSING_CHECKOUT' && !editing && (
          <div className="mt-4 flex items-start gap-2 text-sm text-warning-800 bg-warning-50 border border-warning-100 p-3 rounded-md">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            This session was never checked out. {canCorrect ? 'Use "Correct" to fix it.' : 'An HR administrator needs to correct it.'}
          </div>
        )}

        {editing ? (
          <div className="mt-6 space-y-4">
            {formError && <div className="text-sm text-danger-700 bg-danger-50 border border-danger-100 p-3 rounded-md">{formError}</div>}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Check In</label>
                <input type="datetime-local" value={checkIn} onChange={e => setCheckIn(e.target.value)}
                  className="h-9 w-full px-3 rounded-md border border-gray-300 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Check Out</label>
                <input type="datetime-local" value={checkOut} onChange={e => setCheckOut(e.target.value)}
                  className="h-9 w-full px-3 rounded-md border border-gray-300 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Correction Reason</label>
              <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2} placeholder="Why is this being corrected?"
                className="w-full px-3 py-2 rounded-md border border-gray-300 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500" />
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
              <Button variant="secondary" onClick={() => setEditing(false)}>Cancel</Button>
              <Button variant="primary" loading={saving} onClick={handleSave}>Save Correction</Button>
            </div>
          </div>
        ) : (
          <>
            <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-6">
              <DetailField icon={LogIn} label="Check In" value={formatDateTime(record.check_in)} />
              <DetailField icon={LogOut} label="Check Out" value={record.check_out ? formatDateTime(record.check_out) : undefined} />
              <DetailField icon={Timer} label="Worked Hours" value={formatMinutes(record.worked_minutes)} />
              <DetailField
                icon={Timer}
                label="Overtime"
                value={record.overtime_minutes === null ? undefined : formatMinutes(record.overtime_minutes)}
              />
            </div>

            <div className="mt-6 pt-5 border-t border-gray-100">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 h-7 w-7 rounded-md bg-gray-50 border border-gray-100 flex items-center justify-center shrink-0">
                  <StickyNote className="w-3.5 h-3.5 text-gray-400" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Correction Notes</p>
                  <p className={`text-sm mt-0.5 ${record.notes ? 'text-gray-900' : 'text-gray-400 italic'}`}>
                    {record.notes || 'No corrections made.'}
                  </p>
                  {record.corrected_by_name && (
                    <p className="text-xs text-gray-400 mt-1">Corrected by {record.corrected_by_name}</p>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </SectionCard>
      <ToastViewport toasts={toasts} />
    </div>
  );
}
