import { useState, useEffect } from 'react';
import api from '../services/api';
import type { Department, JobPosition, WorkingScheduleSummary, EmployeeMinimal } from '../types';
import { SearchableSelect } from './SearchableSelect';
import { Drawer } from './ui/Drawer';
import { Button } from './ui/Button';
import { AlertTriangle } from 'lucide-react';

interface ContractFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
  fixedEmployee?: EmployeeMinimal;
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs font-medium text-gray-600 mb-1.5">{children}</label>;
}

const inputClass = 'block w-full h-9 px-3 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500';

export function ContractFormModal({ isOpen, onClose, onSaved, fixedEmployee }: ContractFormModalProps) {
  const [employeeId, setEmployeeId] = useState<number | null>(fixedEmployee?.id ?? null);
  const [departmentId, setDepartmentId] = useState<number | null>(null);
  const [jobPositionId, setJobPositionId] = useState<number | null>(null);
  const [scheduleId, setScheduleId] = useState<number | null>(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [wage, setWage] = useState('');
  const [note, setNote] = useState('');

  const [employees, setEmployees] = useState<EmployeeMinimal[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [jobPositions, setJobPositions] = useState<JobPosition[]>([]);
  const [schedules, setSchedules] = useState<WorkingScheduleSummary[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<{ message: string; conflictRef?: string } | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setError(null);
    setEmployeeId(fixedEmployee?.id ?? null);
    setDepartmentId(null);
    setJobPositionId(null);
    setScheduleId(null);
    setStartDate('');
    setEndDate('');
    setWage('');
    setNote('');

    Promise.all([
      api.get('/employees', { params: { limit: 500 } }),
      api.get('/departments'),
      api.get('/job-positions'),
      api.get('/working-schedules'),
    ]).then(([emps, depts, jps, ws]) => {
      setEmployees(emps.data);
      setDepartments(depts.data);
      setJobPositions(jps.data);
      setSchedules(ws.data);
    });
  }, [isOpen, fixedEmployee]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.post('/contracts', {
        employee_id: employeeId,
        department_id: departmentId,
        job_position_id: jobPositionId,
        working_schedule_id: scheduleId,
        start_date: startDate,
        end_date: endDate || null,
        wage_monthly: parseFloat(wage),
        currency: 'INR',
        salary_structure_note: note || null,
      });
      onSaved();
      onClose();
    } catch (err: any) {
      const detail = err.response?.data?.detail?.error;
      setError({
        message: detail?.message || 'Failed to create contract.',
        conflictRef: detail?.details?.conflicting_contract_reference,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title="New Contract"
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={saving} disabled={!employeeId || !departmentId || !jobPositionId} form="contract-form" type="submit">
            Create Contract
          </Button>
        </div>
      }
    >
      <form id="contract-form" onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="flex items-start gap-2 text-sm text-red-700 bg-red-50 border border-red-100 p-3 rounded-md">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <span>
              {error.message}
              {error.conflictRef && <> Conflicting contract: <strong>{error.conflictRef}</strong>.</>}
            </span>
          </div>
        )}

        <div>
          <FieldLabel>Employee</FieldLabel>
          {fixedEmployee ? (
            <div className="h-9 flex items-center rounded-md border border-gray-200 bg-gray-50 px-3 text-sm text-gray-700">
              {fixedEmployee.first_name} {fixedEmployee.last_name}
            </div>
          ) : (
            <SearchableSelect
              value={employeeId}
              onChange={setEmployeeId}
              options={employees.map(e => ({ id: e.id, label: `${e.first_name} ${e.last_name}`, sublabel: e.work_email || undefined }))}
              placeholder="Select employee"
              clearable={false}
            />
          )}
        </div>

        <div>
          <FieldLabel>Department</FieldLabel>
          <SearchableSelect value={departmentId} onChange={setDepartmentId} options={departments.map(d => ({ id: d.id, label: d.name }))} placeholder="Select department" clearable={false} />
        </div>
        <div>
          <FieldLabel>Job Position</FieldLabel>
          <SearchableSelect value={jobPositionId} onChange={setJobPositionId} options={jobPositions.map(p => ({ id: p.id, label: p.title }))} placeholder="Select job position" clearable={false} />
        </div>
        <div>
          <FieldLabel>Working Schedule</FieldLabel>
          <SearchableSelect value={scheduleId} onChange={setScheduleId} options={schedules.map(s => ({ id: s.id, label: s.name, sublabel: `${s.hours_per_week}h/week` }))} placeholder="Select schedule" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel>Start Date</FieldLabel>
            <input required type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className={inputClass} />
          </div>
          <div>
            <FieldLabel>End Date <span className="text-gray-400 font-normal">(optional)</span></FieldLabel>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className={inputClass} />
          </div>
        </div>

        <div>
          <FieldLabel>Wage / Month (₹)</FieldLabel>
          <input required type="number" min="0.01" step="0.01" value={wage} onChange={e => setWage(e.target.value)} className={inputClass} />
        </div>

        <div>
          <FieldLabel>Notes <span className="text-gray-400 font-normal">(Salary Structure — deferred)</span></FieldLabel>
          <textarea value={note} onChange={e => setNote(e.target.value)} rows={2}
            className="block w-full px-3 py-2 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500" />
        </div>
      </form>
    </Drawer>
  );
}
