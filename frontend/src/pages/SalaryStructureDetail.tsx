import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import type { SalaryStructureDetail as SalaryStructureDetailType, SalaryRule } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { SalaryRuleFormDrawer } from '../components/SalaryRuleFormDrawer';
import { SectionCard } from '../components/ui/SectionCard';
import { SkeletonDetail } from '../components/ui/Skeleton';
import { Button } from '../components/ui/Button';
import { useToast, ToastViewport } from '../components/Toast';
import { formatMoney } from '../lib/format';
import { ArrowLeft, Pencil, Plus } from 'lucide-react';

const PAYROLL_MANAGER_ROLES = ['HR_PAYROLL_MANAGER', 'ADMIN'];

function methodSummary(rule: SalaryRule): string {
  if (rule.computation_method === 'FIXED') return `Fixed ${formatMoney(rule.fixed_amount || '0')}`;
  if (rule.computation_method === 'PERCENTAGE') return `${rule.percentage}% of ${rule.percentage_base === 'CONTRACT_WAGE' ? 'Contract Wage' : rule.percentage_base}`;
  return rule.formula_expression || '';
}

export function SalaryStructureDetail() {
  const { structureId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toasts, push } = useToast();
  const canManage = !!user && PAYROLL_MANAGER_ROLES.includes(user.role);

  const [structure, setStructure] = useState<SalaryStructureDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [ruleDrawer, setRuleDrawer] = useState<{ open: boolean; rule: SalaryRule | null }>({ open: false, rule: null });

  const fetchStructure = () => {
    setLoading(true);
    setError(false);
    api.get(`/payroll/structures/${structureId}`)
      .then(res => setStructure(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(fetchStructure, [structureId]);

  const startEditing = () => {
    if (!structure) return;
    setName(structure.name); setDescription(structure.description || ''); setIsActive(structure.is_active);
    setEditing(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await api.patch(`/payroll/structures/${structureId}`, { name, description: description || null, is_active: isActive });
      setStructure(s => s ? { ...s, ...res.data } : s);
      setEditing(false);
      push('Salary Structure updated.');
    } catch (err: any) {
      push(err.response?.data?.detail?.error?.message || 'Failed to save.', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-5 max-w-3xl">
        <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
        <SkeletonDetail />
      </div>
    );
  }

  if (error || !structure) {
    return (
      <div className="text-center py-16">
        <h2 className="text-base font-semibold text-gray-800">Salary Structure not found</h2>
        <Button variant="ghost" className="mt-4" onClick={() => navigate('/payroll/salary-structures')}>← Back to Salary Structures</Button>
      </div>
    );
  }

  const earlierCodes = (rule: SalaryRule | null) =>
    structure.rules.filter(r => !rule || r.sequence < rule.sequence).map(r => r.code);

  return (
    <div className="space-y-5 max-w-3xl">
      <button onClick={() => navigate('/payroll/salary-structures')} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back
      </button>

      <SectionCard>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Salary Structure</p>
            {editing ? (
              <input value={name} onChange={e => setName(e.target.value)} className="mt-1 h-8 px-2 rounded-md border border-gray-300 text-base font-semibold" />
            ) : (
              <h1 className="text-lg font-semibold text-gray-900 mt-0.5">{structure.name}</h1>
            )}
            {structure.code && <p className="text-sm text-gray-500">{structure.code}</p>}
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={structure.is_active ? 'ACTIVE' : 'INACTIVE'} />
            {canManage && !editing && (
              <Button variant="secondary" size="sm" onClick={startEditing}><Pencil className="w-3.5 h-3.5" /> Edit</Button>
            )}
          </div>
        </div>

        {editing ? (
          <div className="mt-5 space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Description</label>
              <textarea value={description} onChange={e => setDescription(e.target.value)} rows={2}
                className="w-full px-3 py-2 rounded-md border border-gray-300 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500" />
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={isActive} onChange={e => setIsActive(e.target.checked)} className="rounded border-gray-300 text-brand-600 focus:ring-brand-500" />
              Active
            </label>
            <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
              <Button variant="secondary" onClick={() => setEditing(false)}>Cancel</Button>
              <Button variant="primary" loading={saving} onClick={handleSave}>Save Changes</Button>
            </div>
          </div>
        ) : (
          <p className={`mt-3 text-sm ${structure.description ? 'text-gray-700' : 'text-gray-400 italic'}`}>{structure.description || 'No description.'}</p>
        )}
      </SectionCard>

      <SectionCard padded={false}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-900">Salary Rules</h2>
          {canManage && (
            <Button variant="secondary" size="sm" onClick={() => setRuleDrawer({ open: true, rule: null })}>
              <Plus className="w-3.5 h-3.5" /> Add Rule
            </Button>
          )}
        </div>
        {structure.rules.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500">
            This structure has no salary rules.<br />Payroll cannot be computed until rules are configured.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Seq</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Rule Name</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Code</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Category</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Computation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {structure.rules.map(r => (
                  <tr key={r.id} onClick={() => canManage && setRuleDrawer({ open: true, rule: r })} className={canManage ? 'hover:bg-gray-50 cursor-pointer transition-colors' : ''}>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-500">{r.sequence}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{r.name}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-mono text-gray-600">{r.code}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600 capitalize">{r.category.toLowerCase()}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{methodSummary(r)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <SalaryRuleFormDrawer
        isOpen={ruleDrawer.open}
        onClose={() => setRuleDrawer({ open: false, rule: null })}
        salaryStructureId={structure.id}
        earlierCodes={earlierCodes(ruleDrawer.rule)}
        rule={ruleDrawer.rule}
        onSaved={() => { fetchStructure(); push(ruleDrawer.rule ? 'Rule updated.' : 'Rule created.'); }}
      />
      <ToastViewport toasts={toasts} />
    </div>
  );
}
