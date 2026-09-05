import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import type { SalaryRule, SalaryStructure } from '../types';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonTable } from '../components/ui/Skeleton';
import { ListOrdered } from 'lucide-react';

export function SalaryRules() {
  const navigate = useNavigate();
  const [rules, setRules] = useState<SalaryRule[]>([]);
  const [structures, setStructures] = useState<Record<number, SalaryStructure>>({});
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [rulesRes, structuresRes] = await Promise.all([
        api.get('/payroll/rules'),
        api.get('/payroll/structures'),
      ]);
      setRules(rulesRes.data);
      setStructures(Object.fromEntries(structuresRes.data.map((s: SalaryStructure) => [s.id, s])));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  return (
    <div className="space-y-5">
      <PageHeader title="Salary Rules" description="Every ordered calculation across all Salary Structures." />

      <div className="bg-white rounded-xl border border-gray-200 shadow-[var(--shadow-elevation)]">
        {loading ? (
          <SkeletonTable rows={5} cols={5} />
        ) : rules.length === 0 ? (
          <EmptyState icon={ListOrdered} title="No salary rules configured." description="Create a Salary Structure and add rules to it." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Rule Name</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Code</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Category</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Structure</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Sequence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {rules.map(r => (
                  <tr key={r.id} onClick={() => navigate(`/payroll/salary-structures/${r.salary_structure_id}`)} className="hover:bg-gray-50 cursor-pointer transition-colors">
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{r.name}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm font-mono text-gray-600">{r.code}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600 capitalize">{r.category.toLowerCase()}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{structures[r.salary_structure_id]?.name || '—'}</td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-500">{r.sequence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
