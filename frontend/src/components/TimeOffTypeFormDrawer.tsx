import { useState, useEffect } from 'react';
import api from '../services/api';
import type { TimeOffType, TimeOffUnit, ApprovalPolicy } from '../types';
import { Drawer } from './ui/Drawer';
import { Button } from './ui/Button';
import { AlertTriangle } from 'lucide-react';

interface TimeOffTypeFormDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs font-medium text-gray-600 mb-1.5">{children}</label>;
}

const inputClass = 'block w-full h-9 px-3 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500';
const selectClass = 'block w-full h-9 px-3 rounded-md border border-gray-300 text-sm text-gray-900 bg-white focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500';

export function TimeOffTypeFormDrawer({ isOpen, onClose, onSaved }: TimeOffTypeFormDrawerProps) {
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [unit, setUnit] = useState<TimeOffUnit>('DAYS');
  const [requiresAllocation, setRequiresAllocation] = useState(true);
  const [approvalPolicy, setApprovalPolicy] = useState<ApprovalPolicy>('MANAGER');
  const [displayColor, setDisplayColor] = useState('#4f46e5');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    setName(''); setCode(''); setUnit('DAYS'); setRequiresAllocation(true);
    setApprovalPolicy('MANAGER'); setDisplayColor('#4f46e5'); setNotes(''); setError('');
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await api.post('/time-off/types', {
        name, code: code || null, unit, requires_allocation: requiresAllocation,
        approval_policy: approvalPolicy, is_active: true,
        display_color: displayColor || null, notes: notes || null,
      } satisfies Partial<TimeOffType>);
      onSaved();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to create Time Off Type.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title="New Time Off Type"
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={saving} disabled={!name} form="type-form" type="submit">Create Type</Button>
        </div>
      }
    >
      <form id="type-form" onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="flex items-start gap-2 text-sm text-red-700 bg-red-50 border border-red-100 p-3 rounded-md">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div>
          <FieldLabel>Type Name</FieldLabel>
          <input required value={name} onChange={e => setName(e.target.value)} className={inputClass} placeholder="e.g. Paid Time Off" />
        </div>
        <div>
          <FieldLabel>Code <span className="text-gray-400 font-normal">(optional, unique)</span></FieldLabel>
          <input value={code} onChange={e => setCode(e.target.value)} className={inputClass} placeholder="e.g. PTO" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel>Unit</FieldLabel>
            <select value={unit} onChange={e => setUnit(e.target.value as TimeOffUnit)} className={selectClass}>
              <option value="DAYS">Days</option>
              <option value="HOURS">Hours</option>
            </select>
          </div>
          <div>
            <FieldLabel>Approval</FieldLabel>
            <select value={approvalPolicy} onChange={e => setApprovalPolicy(e.target.value as ApprovalPolicy)} className={selectClass}>
              <option value="MANAGER">Manager</option>
              <option value="HR">HR</option>
              <option value="NONE">None (auto-approve)</option>
            </select>
          </div>
        </div>

        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={requiresAllocation} onChange={e => setRequiresAllocation(e.target.checked)} className="rounded border-gray-300 text-brand-600 focus:ring-brand-500" />
          Requires Allocation
        </label>

        <div>
          <FieldLabel>Display Color</FieldLabel>
          <input type="color" value={displayColor} onChange={e => setDisplayColor(e.target.value)} className="h-9 w-16 rounded-md border border-gray-300 cursor-pointer" />
        </div>

        <div>
          <FieldLabel>Configuration Notes <span className="text-gray-400 font-normal">(optional)</span></FieldLabel>
          <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2}
            className="block w-full px-3 py-2 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500" />
        </div>
      </form>
    </Drawer>
  );
}
