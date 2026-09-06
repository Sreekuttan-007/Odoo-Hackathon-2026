import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { Attendance, Contract, Department, Employee, TimeOffRequest } from '../types';
import {
  ArrowRight,
  BriefcaseBusiness,
  Building2,
  CalendarCheck,
  CheckCircle2,
  Clock3,
  FileText,
  PlaneTakeoff,
  Users,
} from 'lucide-react';

const HR_ROLES = ['HR_MANAGER', 'HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];
// Matches the route guard on /payroll/payruns in App.tsx
const PAYROLL_OPERATOR_ROLES = ['HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value));
}

function getInitials(employee: Employee['first_name'], lastName: Employee['last_name']) {
  return `${employee[0] ?? ''}${lastName[0] ?? ''}`.toUpperCase();
}

function StatCard({
  label,
  value,
  detail,
  icon: Icon,
  tone,
}: {
  label: string;
  value: number;
  detail: string;
  icon: typeof Users;
  tone: 'indigo' | 'green' | 'amber' | 'orange';
}) {
  const tones = {
    indigo: 'bg-brand-50 text-brand-700',
    green: 'bg-brand-50 text-brand-700',
    amber: 'bg-warning-50 text-warning-700',
    orange: 'bg-orange-50 text-orange-700',
  };

  return (
    <div className="bezel">
      <div className="bezel-core p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</p>
            <p className="mt-2 text-3xl font-bold tracking-tight text-gray-900 font-display">{value}</p>
          </div>
          <div className={`rounded-xl p-2.5 ${tones[tone]}`}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
        <span className="mt-3 inline-flex rounded-full bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-500">{detail}</span>
      </div>
    </div>
  );
}

export function Dashboard() {
  const { user } = useAuth();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [attendance, setAttendance] = useState<Attendance[]>([]);
  const [requests, setRequests] = useState<TimeOffRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [failedSections, setFailedSections] = useState<string[]>([]);

  useEffect(() => {
    const today = new Date().toISOString().slice(0, 10);
    const loadDashboard = async () => {
      const results = await Promise.allSettled([
        api.get('/employees', { params: { limit: 500 } }),
        api.get('/departments'),
        api.get('/contracts'),
        api.get('/attendance', { params: { on_date: today } }),
        api.get('/time-off/requests'),
      ]);
      const failures: string[] = [];
      const setters = [
        (data: Employee[]) => setEmployees(data),
        (data: Department[]) => setDepartments(data),
        (data: Contract[]) => setContracts(data),
        (data: Attendance[]) => setAttendance(data),
        (data: TimeOffRequest[]) => setRequests(data),
      ];
      const names = ['employees', 'departments', 'contracts', 'attendance', 'time off'];
      results.forEach((result, index) => {
        if (result.status === 'fulfilled') setters[index](result.value.data);
        else failures.push(names[index]);
      });
      setFailedSections(failures);
      setLoading(false);
    };
    loadDashboard();
  }, []);

  const activeEmployees = employees.filter(employee => employee.status === 'ACTIVE');
  const pendingRequests = requests.filter(request => request.status === 'TO_APPROVE');
  const activeContracts = contracts.filter(contract => contract.status === 'RUNNING');
  const checkedIn = attendance.filter(record => record.status === 'ACTIVE').length;
  const missingCheckout = attendance.filter(record => record.status === 'MISSING_CHECKOUT').length;
  const canReview = !!user && HR_ROLES.includes(user.role);
  const canRunPayroll = !!user && PAYROLL_OPERATOR_ROLES.includes(user.role);

  const departmentCounts = useMemo(() => {
    return departments
      .map(department => ({
        ...department,
        count: activeEmployees.filter(employee => employee.department_id === department.id).length,
      }))
      .sort((a, b) => b.count - a.count);
  }, [activeEmployees, departments]);

  const recentRequests = requests
    .filter(request => request.status === 'TO_APPROVE')
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  return (
    <div className="space-y-6">
      <section
        className="relative overflow-hidden rounded-[1.75rem] px-6 py-8 text-white sm:px-9"
        style={{
          background:
            'radial-gradient(120% 140% at 100% 0%, rgb(31 153 115 / 0.45), transparent 55%), #093226',
          boxShadow: 'var(--shadow-popover)',
        }}
      >
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage:
              'linear-gradient(rgb(255 255 255) 1px, transparent 1px), linear-gradient(90deg, rgb(255 255 255) 1px, transparent 1px)',
            backgroundSize: '36px 36px',
          }}
        />
        <div className="relative flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
          <div>
            <span className="eyebrow bg-white/10 text-brand-200">Payloom workspace</span>
            <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl font-display">
              Good to see you, {user?.employee?.first_name ?? 'there'}.
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-6 text-brand-100">
              A current view of your workforce, attendance, contracts, and time-off activity.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Link to="/employees" className="btn-pill-cta bg-white text-brand-900 hover:bg-brand-50 shadow-none hover:shadow-none">
              View employees
              <span className="btn-pill-cta-icon bg-brand-900/10">
                <Users className="h-4 w-4" />
              </span>
            </Link>
            {canReview && (
              <Link to="/time-off/requests?status=TO_APPROVE" className="inline-flex items-center gap-2 rounded-full border border-white/25 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-white/10">
                <PlaneTakeoff className="h-4 w-4" /> Review requests
              </Link>
            )}
          </div>
        </div>
      </section>

      {failedSections.length > 0 && (
        <div className="rounded-lg border border-warning-200 bg-warning-50 px-4 py-3 text-sm text-warning-800">
          Some dashboard sections could not be loaded: {failedSections.join(', ')}. The available sections are still shown.
        </div>
      )}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map(item => <div key={item} className="h-36 animate-pulse rounded-xl bg-gray-100" />)}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Active employees" value={activeEmployees.length} detail={`${employees.length} total employee records`} icon={Users} tone="indigo" />
          <StatCard label="Checked in today" value={checkedIn} detail={`${missingCheckout} missing check-outs`} icon={CalendarCheck} tone="green" />
          <StatCard label="Pending requests" value={pendingRequests.length} detail={canReview ? 'Awaiting review' : 'Your open requests'} icon={PlaneTakeoff} tone="amber" />
          <StatCard label="Running contracts" value={activeContracts.length} detail={`${contracts.length} total contract records`} icon={FileText} tone="orange" />
        </div>
      )}

      <div className="grid items-stretch gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <section className="bezel flex flex-col">
        <div className="bezel-core flex flex-1 flex-col">
          <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
            <div>
              <h2 className="font-semibold text-gray-900 font-display">Pending time-off requests</h2>
              <p className="mt-1 text-sm text-gray-500">Requests that need attention.</p>
            </div>
            <Link to="/time-off/requests" className="inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:text-brand-900">
              See all <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="flex flex-1 flex-col divide-y divide-gray-100">
            {recentRequests.length === 0 ? (
              <div className="flex flex-1 flex-col items-center justify-center px-5 py-12 text-center">
                <CheckCircle2 className="h-8 w-8 text-brand-500" />
                <p className="mt-3 text-sm font-medium text-gray-900">Nothing needs review</p>
                <p className="mt-1 text-sm text-gray-500">New requests will appear here.</p>
              </div>
            ) : recentRequests.map(request => (
              <Link key={request.id} to={`/time-off/requests/${request.id}`} className="flex items-center justify-between gap-4 px-5 py-4 transition hover:bg-gray-50">
                <div className="flex min-w-0 items-center gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-50 text-xs font-semibold text-brand-700">
                    {getInitials(request.employee.first_name, request.employee.last_name)}
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-gray-900">{request.employee.first_name} {request.employee.last_name}</p>
                    <p className="truncate text-xs text-gray-500">{request.time_off_type.name} · {request.duration_amount} {request.time_off_type.unit.toLowerCase()}</p>
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-xs font-medium text-gray-700">{formatDate(request.start_date)}</p>
                  <p className="mt-1 text-xs text-warning-700">To approve</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
        </section>

        <section className="bezel flex flex-col">
        <div className="bezel-core flex flex-1 flex-col">
          <div className="border-b border-gray-100 px-5 py-4">
            <h2 className="font-semibold text-gray-900 font-display">Workforce by department</h2>
            <p className="mt-1 text-sm text-gray-500">Active employees grouped by organization.</p>
          </div>
          <div className="flex-1 space-y-4 p-5">
            {departmentCounts.length === 0 ? (
              <p className="py-6 text-center text-sm text-gray-500">No department data available.</p>
            ) : departmentCounts.map(department => {
              const percentage = activeEmployees.length ? Math.round((department.count / activeEmployees.length) * 100) : 0;
              return (
                <div key={department.id}>
                  <div className="mb-1.5 flex items-center justify-between text-sm">
                    <span className="font-medium text-gray-700">{department.name}</span>
                    <span className="text-gray-500">{department.count}</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                    <div className="h-full rounded-full bg-brand-600" style={{ width: `${percentage}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
          {canReview && (
            <div className="grid grid-cols-2 border-t border-gray-100">
              <Link to="/departments" className="flex items-center gap-2 px-5 py-3 text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900"><Building2 className="h-4 w-4" /> Departments</Link>
              <Link to="/working-schedules" className="flex items-center gap-2 border-l border-gray-100 px-5 py-3 text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900"><Clock3 className="h-4 w-4" /> Schedules</Link>
            </div>
          )}
        </div>
        </section>
      </div>

      <section className="grid gap-4 sm:grid-cols-3">
        <Link to="/attendance" className="bezel group">
          <div className="bezel-core p-5 transition group-hover:-translate-y-0.5">
            <CalendarCheck className="h-5 w-5 text-brand-600" />
            <h2 className="mt-4 font-semibold text-gray-900 font-display">Attendance</h2>
            <p className="mt-1 text-sm text-gray-500">Review today&apos;s workday records and missing check-outs.</p>
            <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-brand-700">Open module <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" /></span>
          </div>
        </Link>
        <Link to="/contracts" className="bezel group">
          <div className="bezel-core p-5 transition group-hover:-translate-y-0.5">
            <BriefcaseBusiness className="h-5 w-5 text-orange-600" />
            <h2 className="mt-4 font-semibold text-gray-900 font-display">Contracts</h2>
            <p className="mt-1 text-sm text-gray-500">Track employment terms, wages, and contract validity.</p>
            <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-brand-700">Open module <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" /></span>
          </div>
        </Link>
        <Link to={canRunPayroll ? '/payroll/payruns' : '/payroll/payslips'} className="bezel group">
          <div className="bezel-core p-5 transition group-hover:-translate-y-0.5">
            <FileText className="h-5 w-5 text-brand-600" />
            <h2 className="mt-4 font-semibold text-gray-900 font-display">Payroll</h2>
            <p className="mt-1 text-sm text-gray-500">{canRunPayroll ? 'Move from workforce overview into payrun processing.' : 'View your payslips and pay history.'}</p>
            <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-brand-700">Open module <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" /></span>
          </div>
        </Link>
      </section>
    </div>
  );
}
