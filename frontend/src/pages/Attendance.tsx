import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import type { Attendance, EmployeeMinimal } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonTable } from '../components/ui/Skeleton';
import { formatDate, formatTime, formatMinutes } from '../lib/format';
import { CalendarCheck, X, AlertTriangle } from 'lucide-react';

export function AttendancePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const employeeId = searchParams.get('employee_id');
  const [filterEmployee, setFilterEmployee] = useState<EmployeeMinimal | null>(null);

  const [records, setRecords] = useState<Attendance[]>([]);
  const [loading, setLoading] = useState(true);
  const [todayOnly, setTodayOnly] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');

  const fetchAttendance = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (employeeId) params.employee_id = employeeId;
      if (statusFilter) params.status = statusFilter;
      if (todayOnly) params.on_date = new Date().toISOString().slice(0, 10);
      const res = await api.get('/attendance', { params });
      setRecords(res.data);
      if (res.data.length > 0 && employeeId) setFilterEmployee(res.data[0].employee);
    } finally {
      setLoading(false);
    }
  }, [employeeId, statusFilter, todayOnly]);

  useEffect(() => {
    if (employeeId) {
      api.get(`/employees/${employeeId}`).then(res => setFilterEmployee(res.data)).catch(() => setFilterEmployee(null));
    } else {
      setFilterEmployee(null);
    }
  }, [employeeId]);

  useEffect(() => { fetchAttendance(); }, [fetchAttendance]);

  const clearEmployeeFilter = () => {
    searchParams.delete('employee_id');
    setSearchParams(searchParams);
  };

  const hasExtraFilters = !!(statusFilter || todayOnly);

  return (
    <div className="space-y-5">
      <PageHeader title="Attendance" description="Check-in/check-out records and worked hours." />

      {employeeId && filterEmployee && (
        <div className="inline-flex items-center gap-2 bg-brand-50 border border-brand-100 text-brand-800 text-sm px-3 py-1.5 rounded-full">
          Employee: <strong className="font-medium">{filterEmployee.first_name} {filterEmployee.last_name}</strong>
          <button onClick={clearEmployeeFilter} className="hover:text-brand-900"><X className="w-3.5 h-3.5" /></button>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-[var(--shadow-elevation)]">
        <div className="p-3.5 border-b border-gray-100 flex flex-col sm:flex-row gap-3 items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setTodayOnly(t => !t)}
              className={`h-9 px-3 rounded-md text-sm font-medium border transition-colors ${todayOnly ? 'bg-brand-600 border-brand-600 text-white' : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'}`}
            >
              Today
            </button>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
              className="h-9 rounded-md border border-gray-300 px-2.5 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500">
              <option value="">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="MISSING_CHECKOUT">Missing Checkout</option>
              <option value="COMPLETED">Completed</option>
            </select>
          </div>
        </div>

        {loading ? (
          <SkeletonTable rows={5} cols={6} />
        ) : records.length === 0 ? (
          <EmptyState
            icon={CalendarCheck}
            title={
              employeeId && filterEmployee
                ? `No attendance records for ${filterEmployee.first_name} in this period.`
                : hasExtraFilters
                  ? 'No attendance records match your filters.'
                  : 'No attendance records for this period.'
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Employee</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Date</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Check In</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Check Out</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Worked Hours</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {records.map(r => (
                  <tr key={r.id} onClick={() => navigate(`/attendance/${r.id}`)} className="hover:bg-gray-50 cursor-pointer transition-colors">
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{r.employee.first_name} {r.employee.last_name}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{formatDate(r.attendance_date)}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{formatTime(r.check_in)}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm">
                      {r.check_out ? (
                        <span className="text-gray-600">{formatTime(r.check_out)}</span>
                      ) : r.status === 'MISSING_CHECKOUT' ? (
                        <span className="inline-flex items-center gap-1 text-warning-700"><AlertTriangle className="w-3.5 h-3.5" /> Missing</span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{formatMinutes(r.worked_minutes)}</td>
                    <td className="px-6 py-3 whitespace-nowrap"><StatusBadge status={r.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
