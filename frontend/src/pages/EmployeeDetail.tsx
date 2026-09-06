import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { Employee } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { EmployeeFormModal } from '../components/EmployeeFormModal';
import { useToast, ToastViewport } from '../components/Toast';
import { Button } from '../components/ui/Button';
import { SectionCard } from '../components/ui/SectionCard';
import { DetailField } from '../components/ui/DetailField';
import { SkeletonDetail } from '../components/ui/Skeleton';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import {
  ArrowLeft, Edit2, Mail, MapPin, Building2, Briefcase, UserCircle2, Clock,
  FileText, CalendarClock, PlaneTakeoff, Lock, Trash2,
} from 'lucide-react';

const HR_ROLES = ['HR_MANAGER', 'HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];

export function EmployeeDetail() {
  const { employeeId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toasts, push } = useToast();
  const canManage = !!user && HR_ROLES.includes(user.role);
  const canDelete = user?.role === 'ADMIN';

  const [employee, setEmployee] = useState<Employee | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [tab, setTab] = useState<'work' | 'private'>('work');
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const fetchEmployee = () => {
    setLoading(true);
    setError(false);
    api.get(`/employees/${employeeId}`)
      .then(res => setEmployee(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(fetchEmployee, [employeeId]);

  const handleDelete = async () => {
    setDeleting(true);
    setDeleteError('');
    try {
      await api.delete(`/employees/${employeeId}`);
      navigate('/employees', { state: { toast: 'Employee removed.' } });
    } catch (err: any) {
      setConfirmingDelete(false);
      setDeleteError(err.response?.data?.detail?.error?.message || 'Failed to remove this employee.');
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-5 max-w-5xl">
        <div className="h-4 w-32 bg-gray-100 rounded animate-pulse" />
        <SkeletonDetail />
      </div>
    );
  }

  if (error || !employee) {
    return (
      <div className="text-center py-16">
        <h2 className="text-base font-semibold text-gray-800">Employee not found</h2>
        <p className="text-sm text-gray-500 mt-1">It may have been removed, or the link is incorrect.</p>
        <Button variant="ghost" className="mt-4" onClick={() => navigate('/employees')}>← Back to Employees</Button>
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-5xl">
      <button onClick={() => navigate('/employees')} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Employees
      </button>

      {deleteError && (
        <div className="text-sm text-danger-700 bg-danger-50 border border-danger-100 p-3 rounded-md">
          {deleteError}
        </div>
      )}

      <SectionCard>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="h-14 w-14 rounded-full bg-brand-50 flex items-center justify-center text-brand-700 font-semibold text-lg shrink-0">
              {employee.first_name[0]}{employee.last_name[0]}
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">{employee.first_name} {employee.last_name}</h1>
              <p className="text-sm text-gray-500">{employee.job_position?.title || 'No job position set'}</p>
              <div className="mt-1.5 flex items-center gap-2">
                <StatusBadge status={employee.status} />
                {employee.employee_code && <span className="text-xs text-gray-400">· {employee.employee_code}</span>}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 self-start">
            {canManage && (
              <Button variant="secondary" size="sm" onClick={() => setIsEditOpen(true)}>
                <Edit2 className="w-3.5 h-3.5" /> Edit
              </Button>
            )}
            {canDelete && (
              <Button variant="destructive" size="sm" onClick={() => setConfirmingDelete(true)}>
                <Trash2 className="w-3.5 h-3.5" /> Remove
              </Button>
            )}
          </div>
        </div>

        {/* Smart actions */}
        <div className="mt-6 grid grid-cols-3 gap-3">
          <Link
            to={`/contracts?employee_id=${employee.id}`}
            className="flex flex-col items-center justify-center gap-1 rounded-lg border border-gray-200 py-3 hover:border-brand-300 hover:bg-brand-50/50 transition-colors duration-150"
          >
            <FileText className="w-4 h-4 text-brand-600" />
            <span className="text-sm font-semibold text-gray-900">{employee.contracts_count}</span>
            <span className="text-xs text-gray-500">Contracts</span>
          </Link>
          <Link
            to={`/attendance?employee_id=${employee.id}`}
            className="flex flex-col items-center justify-center gap-1 rounded-lg border border-gray-200 py-3 hover:border-brand-300 hover:bg-brand-50/50 transition-colors duration-150"
          >
            <CalendarClock className="w-4 h-4 text-brand-600" />
            <span className="text-sm font-semibold text-gray-900">{employee.attendance_count}</span>
            <span className="text-xs text-gray-500">Attendance</span>
          </Link>
          <Link
            to={`/time-off/requests?employee_id=${employee.id}`}
            className="flex flex-col items-center justify-center gap-1 rounded-lg border border-gray-200 py-3 hover:border-brand-300 hover:bg-brand-50/50 transition-colors duration-150"
          >
            <PlaneTakeoff className="w-4 h-4 text-brand-600" />
            <span className="text-sm font-semibold text-gray-900">{employee.time_off_requests_count}</span>
            <span className="text-xs text-gray-500">Time Off</span>
          </Link>
        </div>
      </SectionCard>

      <SectionCard padded={false}>
        <div className="flex border-b border-gray-100 px-6">
          <button onClick={() => setTab('work')} className={`py-3 px-3 text-sm font-medium border-b-2 -mb-px transition-colors ${tab === 'work' ? 'border-brand-600 text-brand-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            Work Information
          </button>
          <button onClick={() => setTab('private')} className={`py-3 px-3 text-sm font-medium border-b-2 -mb-px transition-colors ${tab === 'private' ? 'border-brand-600 text-brand-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            Private Information
          </button>
        </div>

        {tab === 'work' ? (
          <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-6">
            <DetailField icon={Building2} label="Department" value={employee.department?.name} />
            <DetailField icon={Briefcase} label="Job Position" value={employee.job_position?.title} />
            <DetailField icon={UserCircle2} label="Manager" value={employee.manager ? `${employee.manager.first_name} ${employee.manager.last_name}` : undefined} />
            <DetailField icon={Clock} label="Working Schedule" value={employee.working_schedule ? `${employee.working_schedule.name} · ${employee.working_schedule.hours_per_week}h/week` : undefined} />
            <DetailField icon={Mail} label="Work Email" value={employee.work_email || undefined} />
            <DetailField icon={MapPin} label="Work Location" value={employee.work_location || undefined} />
          </div>
        ) : (
          <div className="p-10 text-center">
            <Lock className="w-6 h-6 text-gray-300 mx-auto mb-2" />
            <p className="text-sm text-gray-500">No private information is captured in this phase.</p>
          </div>
        )}
      </SectionCard>

      <EmployeeFormModal
        isOpen={isEditOpen}
        onClose={() => setIsEditOpen(false)}
        employee={employee}
        onSaved={(updated) => { setEmployee(updated); push('Employee updated.'); }}
      />
      <ConfirmDialog
        isOpen={confirmingDelete}
        title="Remove this employee?"
        message={`This permanently deletes ${employee.first_name} ${employee.last_name}'s record. It only succeeds if they have no contracts, attendance, payslips, time off, or a linked login — if they have any history, set their status to Inactive instead.\n\nDo you wish to proceed?`}
        confirmLabel="Remove"
        cancelLabel="Cancel"
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setConfirmingDelete(false)}
      />
      <ToastViewport toasts={toasts} />
    </div>
  );
}
