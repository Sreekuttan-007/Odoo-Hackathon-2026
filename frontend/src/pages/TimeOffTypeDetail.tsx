import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { TimeOffType, TimeOffUnit, ApprovalPolicy } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { SectionCard } from '../components/ui/SectionCard';
import { DetailField } from '../components/ui/DetailField';
import { SkeletonDetail } from '../components/ui/Skeleton';
import { Button } from '../components/ui/Button';
import { useToast, ToastViewport } from '../components/Toast';
import { ArrowLeft, Pencil, Tag, Layers, ShieldCheck, Palette, StickyNote, AlertTriangle } from 'lucide-react';

const HR_ROLES = ['HR_MANAGER', 'HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];

const inputClass = 'block w-full h-9 px-3 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500';
const selectClass = 'block w-full h-9 px-3 rounded-md border border-gray-300 text-sm text-gray-900 bg-white focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500';

export function TimeOffTypeDetail() {
  const { typeId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toasts, push } = useToast();
  const canManage = !!user && HR_ROLES.includes(user.role);

  const [type, setType] = useState<TimeOffType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  const [name, setName] = useState('');
  const [unit, setUnit] = useState<TimeOffUnit>('DAYS');
  const [requiresAllocation, setRequiresAllocation] = useState(true);
  const [approvalPolicy, setApprovalPolicy] = useState<ApprovalPolicy>('MANAGER');
  const [isActive, setIsActive] = useState(true);
  const [displayColor, setDisplayColor] = useState('#4f46e5');
  const [notes, setNotes] = useState('');

  const fetchType = () => {
    setLoading(true);
    setError(false);
    api.get(`/time-off/types/${typeId}`)
      .then(res => setType(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(fetchType, [typeId]);

  const startEditing = () => {
    if (!type) return;
    setName(type.name); setUnit(type.unit); setRequiresAllocation(type.requires_allocation);
    setApprovalPolicy(type.approval_policy); setIsActive(type.is_active);
    setDisplayColor(type.display_color || '#4f46e5'); setNotes(type.notes || '');
    setFormError('');
    setEditing(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setFormError('');
    try {
      const res = await api.patch(`/time-off/types/${typeId}`, {
        name, unit, requires_allocation: requiresAllocation, approval_policy: approvalPolicy,
        is_active: isActive, display_color: displayColor || null, notes: notes || null,
      });
      setType(res.data);
      setEditing(false);
      push('Time Off Type updated.');
    } catch (err: any) {
      setFormError(err.response?.data?.detail?.error?.message || 'Failed to save changes.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-5 max-w-2xl">
        <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
        <SkeletonDetail />
      </div>
    );
  }

  if (error || !type) {
    return (
      <div className="text-center py-16">
        <h2 className="text-base font-semibold text-gray-800">Time Off Type not found</h2>
        <Button variant="ghost" className="mt-4" onClick={() => navigate('/time-off/types')}>← Back to Time Off Types</Button>
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-2xl">
      <button onClick={() => navigate('/time-off/types')} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back
      </button>

      <SectionCard>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Time Off Type</p>
            <h1 className="text-lg font-semibold text-gray-900 mt-0.5 flex items-center gap-2">
              {type.display_color && <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: type.display_color }} />}
              {type.name}
            </h1>
            {type.code && <p className="text-sm text-gray-500">{type.code}</p>}
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={type.is_active ? 'ACTIVE' : 'INACTIVE'} />
            {canManage && !editing && (
              <Button variant="secondary" size="sm" onClick={startEditing}>
                <Pencil className="w-3.5 h-3.5" /> Edit
              </Button>
            )}
          </div>
        </div>

        {editing ? (
          <div className="mt-6 space-y-4">
            {formError && <div className="text-sm text-danger-700 bg-danger-50 border border-danger-100 p-3 rounded-md">{formError}</div>}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Type Name</label>
              <input value={name} onChange={e => setName(e.target.value)} className={inputClass} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Unit</label>
                <select value={unit} onChange={e => setUnit(e.target.value as TimeOffUnit)} className={selectClass}>
                  <option value="DAYS">Days</option>
                  <option value="HOURS">Hours</option>
                </select>
                {unit !== type.unit && (
                  <p className="mt-1 text-xs text-warning-700 flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> Blocked if this type is already referenced.</p>
                )}
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Approval</label>
                <select value={approvalPolicy} onChange={e => setApprovalPolicy(e.target.value as ApprovalPolicy)} className={selectClass}>
                  <option value="MANAGER">Manager</option>
                  <option value="HR">HR</option>
                  <option value="NONE">None (auto-approve)</option>
                </select>
              </div>
            </div>
            <div className="flex items-center gap-6">
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input type="checkbox" checked={requiresAllocation} onChange={e => setRequiresAllocation(e.target.checked)} className="rounded border-gray-300 text-brand-600 focus:ring-brand-500" />
                Requires Allocation
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input type="checkbox" checked={isActive} onChange={e => setIsActive(e.target.checked)} className="rounded border-gray-300 text-brand-600 focus:ring-brand-500" />
                Active
              </label>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Display Color</label>
              <input type="color" value={displayColor} onChange={e => setDisplayColor(e.target.value)} className="h-9 w-16 rounded-md border border-gray-300 cursor-pointer" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Configuration Notes</label>
              <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2}
                className="w-full px-3 py-2 rounded-md border border-gray-300 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500" />
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
              <Button variant="secondary" onClick={() => setEditing(false)}>Cancel</Button>
              <Button variant="primary" loading={saving} onClick={handleSave}>Save Changes</Button>
            </div>
          </div>
        ) : (
          <>
            <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-6">
              <DetailField icon={Layers} label="Unit" value={type.unit === 'DAYS' ? 'Days' : 'Hours'} />
              <DetailField icon={Tag} label="Requires Allocation" value={type.requires_allocation ? 'Required' : 'Not required'} />
              <DetailField icon={ShieldCheck} label="Approval Policy" value={type.approval_policy === 'NONE' ? 'None (auto-approve)' : type.approval_policy === 'HR' ? 'HR' : 'Manager'} />
              <DetailField icon={Palette} label="Display Color" valueNode={
                type.display_color ? (
                  <span className="inline-flex items-center gap-1.5 mt-0.5 text-sm text-gray-900">
                    <span className="h-3 w-3 rounded-full border border-gray-200" style={{ backgroundColor: type.display_color }} /> {type.display_color}
                  </span>
                ) : undefined
              } />
            </div>
            <div className="mt-6 pt-5 border-t border-gray-100">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 h-7 w-7 rounded-md bg-gray-50 border border-gray-100 flex items-center justify-center shrink-0">
                  <StickyNote className="w-3.5 h-3.5 text-gray-400" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Configuration Notes</p>
                  <p className={`text-sm mt-0.5 ${type.notes ? 'text-gray-900' : 'text-gray-400 italic'}`}>{type.notes || 'No notes.'}</p>
                </div>
              </div>
            </div>
          </>
        )}
      </SectionCard>
      <ToastViewport toasts={toasts} />
    </div>
  );
}
