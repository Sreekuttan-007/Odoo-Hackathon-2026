import { useState, useEffect } from 'react';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { TimeOffType, EmployeeMinimal, TimeOffBalance } from '../types';
import { SearchableSelect } from './SearchableSelect';
import { Drawer } from './ui/Drawer';
import { Button } from './ui/Button';
import { formatAmount } from '../lib/format';
import { AlertTriangle } from 'lucide-react';

const HR_ROLES = ['HR_MANAGER', 'HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];

interface TimeOffRequestFormDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
  fixedEmployee?: EmployeeMinimal;
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs font-medium text-gray-600 mb-1.5">{children}</label>;
}

const inputClass = 'block w-full h-9 px-3 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500';

export function TimeOffRequestFormDrawer({ isOpen, onClose, onSaved, fixedEmployee }: TimeOffRequestFormDrawerProps) {
  const { user } = useAuth();
  const canPickEmployee = !!user && HR_ROLES.includes(user.role);

  const [employeeId, setEmployeeId] = useState<number | null>(fixedEmployee?.id ?? (canPickEmployee ? null : user?.employee_id ?? null));
  const [typeId, setTypeId] = useState<number | null>(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [reason, setReason] = useState('');

  const [employees, setEmployees] = useState<EmployeeMinimal[]>([]);
  const [types, setTypes] = useState<TimeOffType[]>([]);
  const [balance, setBalance] = useState<TimeOffBalance | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    setError('');
    setEmployeeId(fixedEmployee?.id ?? (canPickEmployee ? null : user?.employee_id ?? null));
    setTypeId(null); setStartDate(''); setEndDate(''); setReason(''); setBalance(null);

    const requests: Promise<any>[] = [api.get('/time-off/types', { params: { is_active: true } })];
    if (canPickEmployee) requests.push(api.get('/employees', { params: { limit: 500 } }));
    Promise.all(requests).then(([tys, emps]) => {
      setTypes(tys.data);
      if (emps) setEmployees(emps.data);
    });
  }, [isOpen, fixedEmployee, canPickEmployee, user]);

  useEffect(() => {
    if (!employeeId || !typeId) { setBalance(null); return; }
    const selectedType = types.find(t => t.id === typeId);
    if (!selectedType?.requires_allocation) { setBalance(null); return; }
    api.get('/time-off/balance', { params: { employee_id: employeeId, time_off_type_id: typeId } })
      .then(res => setBalance(res.data))
      .catch(() => setBalance(null));
  }, [employeeId, typeId, types]);

  const selectedType = types.find(t => t.id === typeId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await api.post('/time-off/requests', {
        employee_id: canPickEmployee ? employeeId : undefined,
        time_off_type_id: typeId,
        start_date: startDate,
        end_date: endDate,
        reason: reason || null,
      });
      onSaved();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to create request.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title="New Time Off Request"
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={saving} disabled={!employeeId || !typeId || !startDate || !endDate} form="request-form" type="submit">
            Submit Request
          </Button>
        </div>
      }
    >
      <form id="request-form" onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="flex items-start gap-2 text-sm text-red-700 bg-red-50 border border-red-100 p-3 rounded-md">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {canPickEmployee && !fixedEmployee && (
          <div>
            <FieldLabel>Employee</FieldLabel>
            <SearchableSelect
              value={employeeId}
              onChange={setEmployeeId}
              options={employees.map(e => ({ id: e.id, label: `${e.first_name} ${e.last_name}`, sublabel: e.work_email || undefined }))}
              placeholder="Select employee"
              clearable={false}
            />
          </div>
        )}
        {fixedEmployee && (
          <div>
            <FieldLabel>Employee</FieldLabel>
            <div className="h-9 flex items-center rounded-md border border-gray-200 bg-gray-50 px-3 text-sm text-gray-700">
              {fixedEmployee.first_name} {fixedEmployee.last_name}
            </div>
          </div>
        )}

        <div>
          <FieldLabel>Time Off Type</FieldLabel>
          <SearchableSelect
            value={typeId}
            onChange={setTypeId}
            options={types.map(t => ({ id: t.id, label: t.name, sublabel: t.requires_allocation ? 'Allocation required' : undefined }))}
            placeholder="Select type"
            clearable={false}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel>Start Date</FieldLabel>
            <input required type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className={inputClass} />
          </div>
          <div>
            <FieldLabel>End Date</FieldLabel>
            <input required type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className={inputClass} />
          </div>
        </div>

        {selectedType?.requires_allocation && balance && (
          <div className="rounded-md border border-brand-100 bg-brand-50 p-3 text-sm text-brand-800">
            <p>{formatAmount(balance.remaining, balance.unit)} available.</p>
            {balance.allocation_id === null && <p className="mt-1 text-amber-700">No approved allocation covers this period yet — the request will be rejected until one exists.</p>}
          </div>
        )}

        <div>
          <FieldLabel>Reason <span className="text-gray-400 font-normal">(optional)</span></FieldLabel>
          <textarea value={reason} onChange={e => setReason(e.target.value)} rows={2}
            className="block w-full px-3 py-2 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500" />
        </div>
      </form>
    </Drawer>
  );
}
