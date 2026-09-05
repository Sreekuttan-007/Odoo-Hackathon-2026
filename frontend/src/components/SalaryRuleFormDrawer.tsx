import { useState, useEffect } from 'react';
import api from '../services/api';
import type { SalaryRule, RuleCategory, ComputationMethod } from '../types';
import { Drawer } from './ui/Drawer';
import { Button } from './ui/Button';
import { AlertTriangle } from 'lucide-react';

interface SalaryRuleFormDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
  salaryStructureId: number;
  earlierCodes: string[];
  rule?: SalaryRule | null;
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs font-medium text-gray-600 mb-1.5">{children}</label>;
}

const inputClass = 'block w-full h-9 px-3 rounded-md border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500';
const selectClass = 'block w-full h-9 px-3 rounded-md border border-gray-300 text-sm text-gray-900 bg-white focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500';

export function SalaryRuleFormDrawer({ isOpen, onClose, onSaved, salaryStructureId, earlierCodes, rule }: SalaryRuleFormDrawerProps) {
  const isEdit = !!rule;
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [category, setCategory] = useState<RuleCategory>('ALLOWANCE');
  const [sequence, setSequence] = useState('10');
  const [method, setMethod] = useState<ComputationMethod>('FIXED');
  const [fixedAmount, setFixedAmount] = useState('');
  const [percentage, setPercentage] = useState('');
  const [percentageBase, setPercentageBase] = useState('CONTRACT_WAGE');
  const [formulaExpression, setFormulaExpression] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    setError('');
    if (rule) {
      setName(rule.name); setCode(rule.code); setCategory(rule.category);
      setSequence(String(rule.sequence)); setMethod(rule.computation_method);
      setFixedAmount(rule.fixed_amount || ''); setPercentage(rule.percentage || '');
      setPercentageBase(rule.percentage_base || 'CONTRACT_WAGE');
      setFormulaExpression(rule.formula_expression || ''); setQuantity(rule.quantity);
    } else {
      setName(''); setCode(''); setCategory('ALLOWANCE'); setSequence('10'); setMethod('FIXED');
      setFixedAmount(''); setPercentage(''); setPercentageBase('CONTRACT_WAGE'); setFormulaExpression(''); setQuantity('1');
    }
  }, [isOpen, rule]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    const payload: Record<string, unknown> = {
      name, code, category, sequence: parseInt(sequence, 10), computation_method: method, quantity: parseFloat(quantity),
      fixed_amount: method === 'FIXED' ? parseFloat(fixedAmount) : null,
      percentage: method === 'PERCENTAGE' ? parseFloat(percentage) : null,
      percentage_base: method === 'PERCENTAGE' ? percentageBase : null,
      formula_expression: method === 'FORMULA' ? formulaExpression : null,
    };
    try {
      if (isEdit) {
        await api.patch(`/payroll/rules/${rule!.id}`, payload);
      } else {
        await api.post(`/payroll/rules?salary_structure_id=${salaryStructureId}`, payload);
      }
      onSaved();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to save rule.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? 'Edit Salary Rule' : 'New Salary Rule'}
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={saving} disabled={!name || !code} form="rule-form" type="submit">{isEdit ? 'Save Changes' : 'Create Rule'}</Button>
        </div>
      }
    >
      <form id="rule-form" onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="flex items-start gap-2 text-sm text-red-700 bg-red-50 border border-red-100 p-3 rounded-md">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div>
          <FieldLabel>Rule Name</FieldLabel>
          <input required value={name} onChange={e => setName(e.target.value)} className={inputClass} placeholder="e.g. House Rent Allowance" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel>Code</FieldLabel>
            <input required value={code} onChange={e => setCode(e.target.value.toUpperCase())} className={inputClass} placeholder="e.g. HRA" />
          </div>
          <div>
            <FieldLabel>Sequence</FieldLabel>
            <input required type="number" value={sequence} onChange={e => setSequence(e.target.value)} className={inputClass} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel>Category</FieldLabel>
            <select value={category} onChange={e => setCategory(e.target.value as RuleCategory)} className={selectClass}>
              <option value="BASIC">Basic</option>
              <option value="ALLOWANCE">Allowance</option>
              <option value="GROSS">Gross</option>
              <option value="DEDUCTION">Deduction</option>
              <option value="NET">Net</option>
            </select>
          </div>
          <div>
            <FieldLabel>Computation</FieldLabel>
            <select value={method} onChange={e => setMethod(e.target.value as ComputationMethod)} className={selectClass}>
              <option value="FIXED">Fixed Amount</option>
              <option value="PERCENTAGE">Percentage</option>
              <option value="FORMULA">Formula</option>
            </select>
          </div>
        </div>

        {method === 'FIXED' && (
          <div>
            <FieldLabel>Amount</FieldLabel>
            <input required type="number" step="0.01" value={fixedAmount} onChange={e => setFixedAmount(e.target.value)} className={inputClass} />
          </div>
        )}

        {method === 'PERCENTAGE' && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <FieldLabel>Percentage</FieldLabel>
              <input required type="number" step="0.01" value={percentage} onChange={e => setPercentage(e.target.value)} className={inputClass} />
            </div>
            <div>
              <FieldLabel>Base</FieldLabel>
              <select value={percentageBase} onChange={e => setPercentageBase(e.target.value)} className={selectClass}>
                <option value="CONTRACT_WAGE">Contract Wage</option>
                {earlierCodes.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>
        )}

        {method === 'FORMULA' && (
          <div>
            <FieldLabel>Formula Expression</FieldLabel>
            <textarea required value={formulaExpression} onChange={e => setFormulaExpression(e.target.value)} rows={2}
              className="w-full px-3 py-2 rounded-md border border-gray-300 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500"
              placeholder='e.g. rules["BASIC"] + rules["HRA"]' />
            <p className="mt-1.5 text-xs text-gray-500">
              Available: contract_wage, worked_days, expected_work_days, worked_hours, overtime_hours, approved_leave_days,
              rules["CODE"], categories["CATEGORY"]. Only earlier-sequenced rules are available.
            </p>
          </div>
        )}

        <div>
          <FieldLabel>Quantity</FieldLabel>
          <input required type="number" step="0.01" value={quantity} onChange={e => setQuantity(e.target.value)} className={inputClass} />
        </div>
      </form>
    </Drawer>
  );
}
