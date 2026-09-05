import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { Employee, Department } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { EmployeeFormModal } from '../components/EmployeeFormModal';
import { useToast, ToastViewport } from '../components/Toast';
import { Button } from '../components/ui/Button';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonTable } from '../components/ui/Skeleton';
import { Search, Plus, LayoutGrid, List as ListIcon, Mail, Briefcase, Building2, Users } from 'lucide-react';

const HR_ROLES = ['HR_MANAGER', 'HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];

type ViewMode = 'kanban' | 'list';

export function Employees() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toasts, push } = useToast();
  const canManage = !!user && HR_ROLES.includes(user.role);

  const [view, setView] = useState<ViewMode>(() => (localStorage.getItem('employees.view') as ViewMode) || 'kanban');
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem('employees.view', view);
  }, [view]);

  useEffect(() => {
    api.get('/departments').then(res => setDepartments(res.data));
  }, []);

  const fetchEmployees = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (search) params.search = search;
      if (departmentFilter) params.department_id = departmentFilter;
      if (statusFilter) params.status = statusFilter;
      const res = await api.get('/employees', { params });
      setEmployees(res.data);
    } finally {
      setLoading(false);
    }
  }, [search, departmentFilter, statusFilter]);

  useEffect(() => {
    const t = setTimeout(fetchEmployees, 250);
    return () => clearTimeout(t);
  }, [fetchEmployees]);

  const openEmployee = (id: number) => navigate(`/employees/${id}`);

  const hasFilters = !!(search || departmentFilter || statusFilter);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Employees"
        description="Browse and manage your workforce."
        action={canManage && (
          <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
            <Plus className="w-4 h-4" /> New Employee
          </Button>
        )}
      />

      <div className="bg-white rounded-xl border border-gray-200 shadow-[var(--shadow-elevation)]">
        <div className="p-3.5 border-b border-gray-100 flex flex-col lg:flex-row gap-3 items-center justify-between">
          <div className="relative w-full lg:w-96">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-3.5 w-3.5 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Search name, email, code or position…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="block w-full h-9 pl-9 pr-3 border border-gray-300 rounded-md bg-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 text-sm"
            />
          </div>

          <div className="flex items-center gap-2 w-full lg:w-auto">
            <select value={departmentFilter} onChange={e => setDepartmentFilter(e.target.value)}
              className="flex-1 lg:flex-none h-9 rounded-md border border-gray-300 px-2.5 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500">
              <option value="">All Departments</option>
              {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
              className="flex-1 lg:flex-none h-9 rounded-md border border-gray-300 px-2.5 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500">
              <option value="">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
            </select>

            <div className="flex items-center rounded-md border border-gray-300 overflow-hidden shrink-0 h-9">
              <button
                onClick={() => setView('kanban')}
                className={`h-full px-2.5 transition-colors ${view === 'kanban' ? 'bg-brand-600 text-white' : 'bg-white text-gray-500 hover:bg-gray-50'}`}
                title="Kanban view"
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setView('list')}
                className={`h-full px-2.5 border-l border-gray-300 transition-colors ${view === 'list' ? 'bg-brand-600 text-white' : 'bg-white text-gray-500 hover:bg-gray-50'}`}
                title="List view"
              >
                <ListIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {loading ? (
          <SkeletonTable rows={6} cols={5} />
        ) : employees.length === 0 ? (
          <EmptyState
            icon={Users}
            title={hasFilters ? 'No employees match your filters.' : 'No employees yet.'}
            description={hasFilters ? 'Try a different search term or clear your filters.' : 'Add your first employee to begin building your workforce.'}
          />
        ) : view === 'kanban' ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 p-4">
            {employees.map(emp => (
              <button
                key={emp.id}
                onClick={() => openEmployee(emp.id)}
                className="text-left bg-white border border-gray-200 rounded-lg p-4 hover:border-brand-300 hover:shadow-[var(--shadow-elevation)] transition-all duration-150 group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="h-10 w-10 rounded-full bg-brand-50 flex items-center justify-center text-brand-700 font-semibold text-sm">
                    {emp.first_name[0]}{emp.last_name[0]}
                  </div>
                  <StatusBadge status={emp.status} />
                </div>
                <h3 className="text-sm font-semibold text-gray-900 group-hover:text-brand-700">{emp.first_name} {emp.last_name}</h3>
                <p className="text-xs text-gray-500 mt-1 flex items-center gap-1.5">
                  <Briefcase className="w-3 h-3 text-gray-400" />
                  {emp.job_position?.title || '—'}
                </p>
                <p className="text-xs text-gray-500 mt-1 flex items-center gap-1.5">
                  <Building2 className="w-3 h-3 text-gray-400" />
                  {emp.department?.name || '—'}
                </p>
              </button>
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Employee</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Work Email</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Job Position</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Department</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {employees.map(emp => (
                  <tr key={emp.id} onClick={() => openEmployee(emp.id)} className="hover:bg-gray-50 cursor-pointer transition-colors">
                    <td className="px-6 py-3 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="h-8 w-8 flex-shrink-0 bg-brand-50 rounded-full flex items-center justify-center text-brand-700 font-semibold text-xs">
                          {emp.first_name[0]}{emp.last_name[0]}
                        </div>
                        <div className="ml-3">
                          <div className="text-sm font-medium text-gray-900">{emp.first_name} {emp.last_name}</div>
                          <div className="text-xs text-gray-400">{emp.employee_code}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">
                      <span className="flex items-center gap-1.5"><Mail className="w-3.5 h-3.5 text-gray-400" />{emp.work_email || '—'}</span>
                    </td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{emp.job_position?.title || '—'}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{emp.department?.name || '—'}</td>
                    <td className="px-6 py-3 whitespace-nowrap"><StatusBadge status={emp.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <EmployeeFormModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSaved={() => { fetchEmployees(); push('Employee created.'); }}
      />
      <ToastViewport toasts={toasts} />
    </div>
  );
}
