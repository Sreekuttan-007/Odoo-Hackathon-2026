import { useState, useEffect } from 'react';
import api from '../services/api';
import { Drawer } from './ui/Drawer';
import { Button } from './ui/Button';
import { AlertTriangle } from 'lucide-react';

interface SalaryStructureFormDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs font-medium text-gray-600 mb-1.5">{children}</label>;
}

const inputClass = 'block w-full h-9 px-3 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500';

export function SalaryStructureFormDrawer({ isOpen, onClose, onSaved }: SalaryStructureFormDrawerProps) {
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    setName(''); setCode(''); setDescription(''); setError('');
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await api.post('/payroll/structures', { name, code: code || null, description: description || null, is_active: true });
      onSaved();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to create structure.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title="New Salary Structure"
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={saving} disabled={!name} form="structure-form" type="submit">Create Structure</Button>
        </div>
      }
    >
      <form id="structure-form" onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="flex items-start gap-2 text-sm text-danger-700 bg-danger-50 border border-danger-100 p-3 rounded-md">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <div>
          <FieldLabel>Structure Name</FieldLabel>
          <input required value={name} onChange={e => setName(e.target.value)} className={inputClass} placeholder="e.g. Regular Salary" />
        </div>
        <div>
          <FieldLabel>Code <span className="text-gray-400 font-normal">(optional, unique)</span></FieldLabel>
          <input value={code} onChange={e => setCode(e.target.value)} className={inputClass} placeholder="e.g. REGULAR" />
        </div>
        <div>
          <FieldLabel>Description <span className="text-gray-400 font-normal">(optional)</span></FieldLabel>
          <textarea value={description} onChange={e => setDescription(e.target.value)} rows={2}
            className="block w-full px-3 py-2 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500" />
        </div>
      </form>
    </Drawer>
  );
}
