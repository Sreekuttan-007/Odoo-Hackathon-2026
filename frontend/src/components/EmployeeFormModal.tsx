import { useState, useEffect } from 'react';
import api from '../services/api';
import type { Employee, Department, JobPosition, WorkingScheduleSummary, EmployeeMinimal, EmployeeStatus } from '../types';
import { SearchableSelect } from './SearchableSelect';
import { Drawer } from './ui/Drawer';
import { Button } from './ui/Button';

interface EmployeeFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: (employee: Employee) => void;
  employee?: Employee | null;
}

interface FormState {
  first_name: string;
  last_name: string;
  work_email: string;
  work_location: string;
  status: EmployeeStatus;
  department_id: number | null;
  job_position_id: number | null;
  manager_id: number | null;
  working_schedule_id: number | null;
}

const EMPTY_FORM: FormState = {
  first_name: '', last_name: '', work_email: '', work_location: '', status: 'ACTIVE',
  department_id: null, job_position_id: null, manager_id: null, working_schedule_id: null,
};

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs font-medium text-gray-600 mb-1.5">{children}</label>;
}

const inputClass = 'block w-full h-9 px-3 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500';

export function EmployeeFormModal({ isOpen, onClose, onSaved, employee }: EmployeeFormModalProps) {
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [jobPositions, setJobPositions] = useState<JobPosition[]>([]);
  const [schedules, setSchedules] = useState<WorkingScheduleSummary[]>([]);
  const [employees, setEmployees] = useState<EmployeeMinimal[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const isEdit = !!employee;

  useEffect(() => {
    if (!isOpen) return;
    setError('');
    setForm(employee ? {
      first_name: employee.first_name,
      last_name: employee.last_name,
      work_email: employee.work_email || '',
      work_location: employee.work_location || '',
      status: employee.status,
      department_id: employee.department_id,
      job_position_id: employee.job_position_id,
      manager_id: employee.manager_id,
      working_schedule_id: employee.working_schedule_id,
    } : EMPTY_FORM);

    Promise.all([
      api.get('/departments'),
      api.get('/job-positions'),
      api.get('/working-schedules'),
      api.get('/employees', { params: { limit: 500 } }),
    ]).then(([d, jp, ws, emps]) => {
      setDepartments(d.data);
      setJobPositions(jp.data);
      setSchedules(ws.data);
      setEmployees(emps.data.filter((e: Employee) => !employee || e.id !== employee.id));
    });
  }, [isOpen, employee]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    const payload = {
      first_name: form.first_name,
      last_name: form.last_name,
      work_email: form.work_email || null,
      work_location: form.work_location || null,
      status: form.status,
      department_id: form.department_id,
      job_position_id: form.job_position_id,
      manager_id: form.manager_id,
      working_schedule_id: form.working_schedule_id,
    };
    try {
      const res = isEdit
        ? await api.patch(`/employees/${employee!.id}`, payload)
        : await api.post('/employees', payload);
      onSaved(res.data);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to save employee.');
    } finally {
      setSaving(false);
    }
  };

  const createDepartment = async (name: string) => {
    const res = await api.post('/departments', { name });
    setDepartments(d => [...d, res.data]);
    return { id: res.data.id, label: res.data.name };
  };

  const createJobPosition = async (title: string) => {
    const res = await api.post('/job-positions', { title });
    setJobPositions(jp => [...jp, res.data]);
    return { id: res.data.id, label: res.data.title };
  };

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? 'Edit Employee' : 'New Employee'}
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={saving} form="employee-form" type="submit">
            {isEdit ? 'Save Changes' : 'Create Employee'}
          </Button>
        </div>
      }
    >
      <form id="employee-form" onSubmit={handleSubmit} className="space-y-6">
        {error && <div className="text-sm text-red-700 bg-red-50 border border-red-100 p-3 rounded-md">{error}</div>}

        <div>
          <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Identity</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <FieldLabel>First Name</FieldLabel>
              <input required value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} className={inputClass} />
            </div>
            <div>
              <FieldLabel>Last Name</FieldLabel>
              <input required value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} className={inputClass} />
            </div>
          </div>
          <div className="mt-4">
            <FieldLabel>Work Email</FieldLabel>
            <input type="email" value={form.work_email} onChange={e => setForm({ ...form, work_email: e.target.value })} className={inputClass} />
          </div>
        </div>

        <div>
          <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Employment</p>
          <div className="space-y-4">
            <div>
              <FieldLabel>Department</FieldLabel>
              <SearchableSelect
                value={form.department_id}
                onChange={id => setForm({ ...form, department_id: id })}
                options={departments.map(d => ({ id: d.id, label: d.name }))}
                placeholder="Select department"
                onCreate={createDepartment}
                createLabel="Create department"
              />
            </div>
            <div>
              <FieldLabel>Job Position</FieldLabel>
              <SearchableSelect
                value={form.job_position_id}
                onChange={id => setForm({ ...form, job_position_id: id })}
                options={jobPositions.map(p => ({ id: p.id, label: p.title }))}
                placeholder="Select job position"
                onCreate={createJobPosition}
                createLabel="Create position"
              />
            </div>
            <div>
              <FieldLabel>Manager</FieldLabel>
              <SearchableSelect
                value={form.manager_id}
                onChange={id => setForm({ ...form, manager_id: id })}
                options={employees.map(e => ({ id: e.id, label: `${e.first_name} ${e.last_name}`, sublabel: e.work_email || undefined }))}
                placeholder="No manager"
              />
            </div>
          </div>
        </div>

        <div>
          <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Work Setup</p>
          <div className="space-y-4">
            <div>
              <FieldLabel>Working Schedule</FieldLabel>
              <SearchableSelect
                value={form.working_schedule_id}
                onChange={id => setForm({ ...form, working_schedule_id: id })}
                options={schedules.map(s => ({ id: s.id, label: s.name, sublabel: `${s.hours_per_week}h/week` }))}
                placeholder="Select schedule"
              />
            </div>
            <div>
              <FieldLabel>Work Location</FieldLabel>
              <input value={form.work_location} onChange={e => setForm({ ...form, work_location: e.target.value })} placeholder="Head Office" className={inputClass} />
            </div>
            <div>
              <FieldLabel>Status</FieldLabel>
              <select value={form.status} onChange={e => setForm({ ...form, status: e.target.value as EmployeeStatus })} className={inputClass}>
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
              </select>
            </div>
          </div>
        </div>
      </form>
    </Drawer>
  );
}
