import { useState, useEffect } from 'react';
import api from '../services/api';
import type { TimeOffType, EmployeeMinimal } from '../types';
import { SearchableSelect } from './SearchableSelect';
import { Drawer } from './ui/Drawer';
import { Button } from './ui/Button';
import { AlertTriangle } from 'lucide-react';

interface AllocationFormDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
  fixedEmployee?: EmployeeMinimal;
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs font-medium text-gray-600 mb-1.5">{children}</label>;
}

const inputClass = 'block w-full h-9 px-3 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500';

export function AllocationFormDrawer({ isOpen, onClose, onSaved, fixedEmployee }: AllocationFormDrawerProps) {
  const [employeeId, setEmployeeId] = useState<number | null>(fixedEmployee?.id ?? null);
  const [typeId, setTypeId] = useState<number | null>(null);
  const [amount, setAmount] = useState('');
  const [validFrom, setValidFrom] = useState('');
  const [validTo, setValidTo] = useState('');
  const [description, setDescription] = useState('');

  const [employees, setEmployees] = useState<EmployeeMinimal[]>([]);
  const [types, setTypes] = useState<TimeOffType[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    setError('');
    setEmployeeId(fixedEmployee?.id ?? null);
    setTypeId(null); setAmount(''); setValidFrom(''); setValidTo(''); setDescription('');

    Promise.all([
      api.get('/employees', { params: { limit: 500 } }),
      api.get('/time-off/types', { params: { is_active: true } }),
    ]).then(([emps, tys]) => {
      setEmployees(emps.data);
      setTypes(tys.data);
    });
  }, [isOpen, fixedEmployee]);

  const selectedType = types.find(t => t.id === typeId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await api.post('/time-off/allocations', {
        employee_id: employeeId,
        time_off_type_id: typeId,
        allocated_amount: parseFloat(amount),
        valid_from: validFrom,
        valid_to: validTo,
        description: description || null,
      });
      onSaved();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to create allocation.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title="New Allocation"
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={saving} disabled={!employeeId || !typeId || !amount || !validFrom || !validTo} form="allocation-form" type="submit">
            Create Allocation
          </Button>
        </div>
      }
    >
      <form id="allocation-form" onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="flex items-start gap-2 text-sm text-danger-700 bg-danger-50 border border-danger-100 p-3 rounded-md">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{error}</span>
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
          <FieldLabel>Time Off Type</FieldLabel>
          <SearchableSelect
            value={typeId}
            onChange={setTypeId}
            options={types.map(t => ({ id: t.id, label: t.name, sublabel: t.unit === 'DAYS' ? 'Days' : 'Hours' }))}
            placeholder="Select type"
            clearable={false}
          />
        </div>

        <div>
          <FieldLabel>Allocated Amount {selectedType && <span className="text-gray-400 font-normal">({selectedType.unit === 'DAYS' ? 'days' : 'hours'})</span>}</FieldLabel>
          <input required type="number" min="0.01" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} className={inputClass} />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel>Valid From</FieldLabel>
            <input required type="date" value={validFrom} onChange={e => setValidFrom(e.target.value)} className={inputClass} />
          </div>
          <div>
            <FieldLabel>Valid To</FieldLabel>
            <input required type="date" value={validTo} onChange={e => setValidTo(e.target.value)} className={inputClass} />
          </div>
        </div>

        <div>
          <FieldLabel>Description <span className="text-gray-400 font-normal">(optional)</span></FieldLabel>
          <textarea value={description} onChange={e => setDescription(e.target.value)} rows={2}
            className="block w-full px-3 py-2 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500" placeholder="e.g. 2026 Annual Balance" />
        </div>
      </form>
    </Drawer>
  );
}
