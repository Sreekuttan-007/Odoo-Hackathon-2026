import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { WorkingSchedule } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonTable } from '../components/ui/Skeleton';
import { Search, Plus, CalendarDays } from 'lucide-react';

const HR_ROLES = ['HR_MANAGER', 'HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];

export function WorkingSchedules() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const canManage = !!user && HR_ROLES.includes(user.role);

  const [schedules, setSchedules] = useState<WorkingSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    setLoading(true);
    const t = setTimeout(() => {
      api.get('/working-schedules', { params: search ? { search } : {} })
        .then(res => setSchedules(res.data))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(t);
  }, [search]);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Working Schedules"
        description="Define the expected working time used by Employees and Contracts."
        action={canManage && (
          <Button variant="primary" onClick={() => navigate('/working-schedules/new')}>
            <Plus className="w-4 h-4" /> New Schedule
          </Button>
        )}
      />

      <div className="bg-white rounded-xl border border-gray-200 shadow-[var(--shadow-elevation)]">
        <div className="p-3.5 border-b border-gray-100">
          <div className="relative w-full sm:w-96">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-3.5 w-3.5 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Search schedules…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="block w-full h-9 pl-9 pr-3 border border-gray-300 rounded-md bg-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 text-sm"
            />
          </div>
        </div>

        {loading ? (
          <SkeletonTable rows={4} cols={5} />
        ) : schedules.length === 0 ? (
          <EmptyState icon={CalendarDays} title="No working schedules configured." description="Create a schedule to define expected working time." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Schedule Name</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Days / Week</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Hours / Week</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Company</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {schedules.map(s => (
                  <tr key={s.id} onClick={() => navigate(`/working-schedules/${s.id}`)} className="hover:bg-gray-50 cursor-pointer transition-colors">
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{s.name}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{s.days_per_week}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{s.hours_per_week}h</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{s.company}</td>
                    <td className="px-6 py-3 whitespace-nowrap"><StatusBadge status={s.status} /></td>
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
