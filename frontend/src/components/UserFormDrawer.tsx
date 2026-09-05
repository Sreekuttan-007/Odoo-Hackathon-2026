import { useState, useEffect } from 'react';
import api from '../services/api';
import type { User } from '../contexts/AuthContext';
import type { Role, EmployeeMinimal } from '../types';
import { Drawer } from './ui/Drawer';
import { Button } from './ui/Button';

interface UserFormDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
  user?: User | null;
}

const ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: 'EMPLOYEE', label: 'Employee' },
  { value: 'HR_MANAGER', label: 'HR Manager' },
  { value: 'HR_PAYROLL_USER', label: 'HR Payroll User' },
  { value: 'HR_PAYROLL_MANAGER', label: 'HR Payroll Manager' },
  { value: 'ADMIN', label: 'Admin' },
];

const inputClass = 'block w-full h-9 px-3 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500';

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs font-medium text-gray-600 mb-1.5">{children}</label>;
}

export function UserFormDrawer({ isOpen, onClose, onSaved, user }: UserFormDrawerProps) {
  const isEdit = !!user;
  const [employees, setEmployees] = useState<EmployeeMinimal[]>([]);
  const [employeeId, setEmployeeId] = useState('');
  const [workEmail, setWorkEmail] = useState('');
  const [role, setRole] = useState<Role>('EMPLOYEE');
  const [status, setStatus] = useState<'ACTIVE' | 'INACTIVE'>('ACTIVE');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    setError('');
    setPassword('');
    if (user) {
      setEmployeeId(String(user.employee_id));
      setWorkEmail(user.work_email);
      setRole(user.role);
      setStatus(user.status as 'ACTIVE' | 'INACTIVE');
    } else {
      setEmployeeId('');
      setWorkEmail('');
      setRole('EMPLOYEE');
      setStatus('ACTIVE');
      api.get('/admin/employees/lookup').then(res => setEmployees(res.data));
    }
  }, [isOpen, user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      if (isEdit) {
        // Only send work_email if it actually changed — the backend validates
        // it as a strict email address, which existing seed/demo accounts
        // (e.g. *.local) do not satisfy even when left untouched.
        const payload: Record<string, unknown> = { role, status };
        if (workEmail !== user!.work_email) payload.work_email = workEmail;
        await api.put(`/admin/users/${user!.id}`, payload);
      } else {
        await api.post('/admin/users', { employee_id: parseInt(employeeId), work_email: workEmail, role, status, password });
      }
      onSaved();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to save user.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? 'Edit User' : 'New User'}
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={loading} form="user-form" type="submit">
            {isEdit ? 'Save Changes' : 'Create User'}
          </Button>
        </div>
      }
    >
      <form id="user-form" onSubmit={handleSubmit} className="space-y-4">
        {error && <div className="text-sm text-danger-700 bg-danger-50 border border-danger-100 p-3 rounded-md">{error}</div>}

        {!isEdit && (
          <div>
            <FieldLabel>Employee</FieldLabel>
            <select
              required
              value={employeeId}
              onChange={(e) => {
                const emp = employees.find(x => x.id === parseInt(e.target.value));
                setEmployeeId(e.target.value);
                if (emp?.work_email) setWorkEmail(emp.work_email);
              }}
              className={inputClass}
            >
              <option value="" disabled>Select employee</option>
              {employees.map(emp => (
                <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name} · {emp.work_email}</option>
              ))}
            </select>
          </div>
        )}

        <div>
          <FieldLabel>Work Email</FieldLabel>
          <input type="email" required value={workEmail} onChange={e => setWorkEmail(e.target.value)} className={inputClass} />
        </div>

        {!isEdit && (
          <div>
            <FieldLabel>Temporary Password</FieldLabel>
            <input type="text" required value={password} onChange={e => setPassword(e.target.value)} className={inputClass} />
          </div>
        )}

        <div>
          <FieldLabel>Role</FieldLabel>
          <select value={role} onChange={e => setRole(e.target.value as Role)} className={inputClass}>
            {ROLE_OPTIONS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </div>

        {isEdit && (
          <div>
            <FieldLabel>Status</FieldLabel>
            <select value={status} onChange={e => setStatus(e.target.value as 'ACTIVE' | 'INACTIVE')} className={inputClass}>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
            </select>
          </div>
        )}
      </form>
    </Drawer>
  );
}
