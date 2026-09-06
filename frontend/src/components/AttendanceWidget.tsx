import { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';
import type { CurrentAttendance } from '../types';
import { formatTime, formatMinutes } from '../lib/format';
import { Button } from './ui/Button';
import { ConfirmDialog } from './ui/ConfirmDialog';
import { Clock, LogIn, LogOut, AlertCircle } from 'lucide-react';

export function AttendanceWidget() {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState<CurrentAttendance | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [now, setNow] = useState(() => Date.now());
  const [confirmingCheckOut, setConfirmingCheckOut] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const refresh = useCallback(() => {
    api.get('/attendance/current').then(res => setCurrent(res.data)).catch(() => {});
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // Live elapsed-time display only — the backend check_in timestamp is the
  // source of truth; nothing is written every tick.
  useEffect(() => {
    if (!current?.checked_in) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [current?.checked_in]);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      // The confirm dialog portals to document.body, outside this popover's
      // own container — ignore outside-clicks while it's open so cancelling
      // the check-out doesn't also collapse the popover underneath it.
      if (confirmingCheckOut) return;
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [confirmingCheckOut]);

  const handleCheckIn = async () => {
    setLoading(true);
    setError('');
    try {
      await api.post('/attendance/check-in');
      refresh();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to check in.');
    } finally {
      setLoading(false);
    }
  };

  const confirmCheckOut = async () => {
    setLoading(true);
    setError('');
    try {
      await api.post('/attendance/check-out');
      refresh();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to check out.');
    } finally {
      setLoading(false);
      setConfirmingCheckOut(false);
    }
  };

  if (!current) return null;

  const checkedIn = current.checked_in;
  const elapsed = checkedIn && current.attendance ? Math.max(0, Math.floor((now - new Date(current.attendance.check_in).getTime()) / 60000)) : 0;

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setOpen(o => !o)}
        className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
          checkedIn ? 'border-brand-200 bg-brand-50 text-brand-700' : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'
        }`}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${checkedIn ? 'bg-brand-500' : 'bg-gray-300'}`} />
        {checkedIn ? `Checked in · ${formatMinutes(elapsed)}` : 'Not checked in'}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-72 rounded-lg border border-gray-200 bg-white shadow-[var(--shadow-popover)] p-4 z-30">
          {error && (
            <div className="flex items-start gap-2 text-xs text-danger-700 bg-danger-50 border border-danger-100 p-2.5 rounded-md mb-3">
              <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              {error}
            </div>
          )}

          {checkedIn && current.attendance ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">Check In</p>
                  <p className="text-gray-900 font-medium">{formatTime(current.attendance.check_in)}</p>
                </div>
                <div>
                  <p className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">Now</p>
                  <p className="text-gray-900 font-medium">{new Date(now).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-sm text-gray-700 bg-gray-50 rounded-md px-3 py-2">
                <Clock className="w-3.5 h-3.5 text-gray-400" />
                Elapsed: <span className="font-semibold text-gray-900">{formatMinutes(elapsed)}</span>
              </div>
              <Button variant="secondary" className="w-full" loading={loading} onClick={() => setConfirmingCheckOut(true)}>
                <LogOut className="w-3.5 h-3.5" /> Check Out
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-gray-500">You haven't checked in today.</p>
              <Button variant="primary" className="w-full" loading={loading} onClick={handleCheckIn}>
                <LogIn className="w-3.5 h-3.5" /> Check In
              </Button>
            </div>
          )}
        </div>
      )}

      <ConfirmDialog
        isOpen={confirmingCheckOut}
        title="End today's work session?"
        message={`You've been checked in for ${formatMinutes(elapsed)}. Checking out now closes today's session — a mis-click here can leave too little worked time for the day to be paid.\n\nDo you wish to proceed?`}
        confirmLabel="Check out"
        cancelLabel="Stay checked in"
        loading={loading}
        onConfirm={confirmCheckOut}
        onCancel={() => setConfirmingCheckOut(false)}
      />
    </div>
  );
}
