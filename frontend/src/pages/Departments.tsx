import { useState, useEffect } from 'react';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { Department } from '../types';
import { useToast, ToastViewport } from '../components/Toast';
import { PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { Skeleton } from '../components/ui/Skeleton';
import { Building2, Plus, Pencil, Check, X } from 'lucide-react';

const HR_ROLES = ['HR_MANAGER', 'HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];

export function Departments() {
  const { user } = useAuth();
  const { toasts, push } = useToast();
  const canManage = !!user && HR_ROLES.includes(user.role);

  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');

  const fetchDepartments = () => {
    setLoading(true);
    api.get('/departments').then(res => setDepartments(res.data)).finally(() => setLoading(false));
  };

  useEffect(fetchDepartments, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await api.post('/departments', { name: newName.trim() });
      setNewName('');
      fetchDepartments();
      push('Department created.');
    } catch (err: any) {
      push(err.response?.data?.detail?.error?.message || 'Failed to create department.', 'error');
    } finally {
      setCreating(false);
    }
  };

  const handleRename = async (id: number) => {
    if (!editValue.trim()) return;
    try {
      await api.patch(`/departments/${id}`, { name: editValue.trim() });
      setEditingId(null);
      fetchDepartments();
      push('Department updated.');
    } catch (err: any) {
      push(err.response?.data?.detail?.error?.message || 'Failed to update department.', 'error');
    }
  };

  return (
    <div className="space-y-5 max-w-2xl">
      <PageHeader title="Departments" description="Structural groups used across Employees and Contracts." />

      {canManage && (
        <form onSubmit={handleCreate} className="flex gap-2">
          <input
            value={newName}
            onChange={e => setNewName(e.target.value)}
            placeholder="New department name…"
            className="flex-1 h-9 rounded-md border border-gray-300 px-3 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500"
          />
          <Button type="submit" variant="primary" loading={creating}>
            <Plus className="w-4 h-4" /> Add
          </Button>
        </form>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-[var(--shadow-elevation)] divide-y divide-gray-50">
        {loading ? (
          <div className="p-5 space-y-4">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-4 w-40" />)}
          </div>
        ) : departments.length === 0 ? (
          <EmptyState icon={Building2} title="No departments yet." description="Add a department to start organizing employees." />
        ) : (
          departments.map(dept => (
            <div key={dept.id} className="flex items-center justify-between px-5 py-3">
              {editingId === dept.id ? (
                <div className="flex items-center gap-2 flex-1">
                  <input
                    autoFocus
                    value={editValue}
                    onChange={e => setEditValue(e.target.value)}
                    className="flex-1 h-8 rounded-md border border-gray-300 px-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                  <button onClick={() => handleRename(dept.id)} className="text-green-600 hover:text-green-700"><Check className="w-4 h-4" /></button>
                  <button onClick={() => setEditingId(null)} className="text-gray-400 hover:text-gray-600"><X className="w-4 h-4" /></button>
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-2.5">
                    <Building2 className="w-3.5 h-3.5 text-gray-400" />
                    <span className="text-sm font-medium text-gray-900">{dept.name}</span>
                  </div>
                  {canManage && (
                    <button onClick={() => { setEditingId(dept.id); setEditValue(dept.name); }} className="text-gray-400 hover:text-brand-600 transition-colors">
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                  )}
                </>
              )}
            </div>
          ))
        )}
      </div>
      <ToastViewport toasts={toasts} />
    </div>
  );
}
