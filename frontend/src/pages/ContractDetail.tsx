import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import type { Contract } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { SectionCard } from '../components/ui/SectionCard';
import { SkeletonDetail } from '../components/ui/Skeleton';
import { Button } from '../components/ui/Button';
import { formatWage, formatPeriod } from '../lib/format';
import { ArrowLeft, Building2, Briefcase, Clock, StickyNote } from 'lucide-react';

export function ContractDetail() {
  const { contractId } = useParams();
  const navigate = useNavigate();
  const [contract, setContract] = useState<Contract | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.get(`/contracts/${contractId}`)
      .then(res => setContract(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [contractId]);

  if (loading) {
    return (
      <div className="space-y-5 max-w-3xl">
        <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
        <SkeletonDetail />
      </div>
    );
  }

  if (error || !contract) {
    return (
      <div className="text-center py-16">
        <h2 className="text-base font-semibold text-gray-800">Contract not found</h2>
        <Button variant="ghost" className="mt-4" onClick={() => navigate('/contracts')}>← Back to Contracts</Button>
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-3xl">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back
      </button>

      <SectionCard>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">{contract.reference}</h1>
            <Link to={`/employees/${contract.employee.id}`} className="text-sm text-brand-600 hover:text-brand-700 font-medium">
              {contract.employee.first_name} {contract.employee.last_name}
            </Link>
          </div>
          <StatusBadge status={contract.status} />
        </div>

        <div className="mt-6 pt-5 border-t border-gray-100">
          <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Employment Period</p>
          <p className="text-sm text-gray-900">{formatPeriod(contract.start_date, contract.end_date)}</p>
        </div>

        <div className="mt-5">
          <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Compensation</p>
          <p className="text-base font-semibold text-gray-900">{formatWage(contract.wage_monthly, contract.currency)}</p>
        </div>

        <div className="mt-6 pt-5 border-t border-gray-100 grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="flex items-start gap-2.5">
            <Briefcase className="w-3.5 h-3.5 text-gray-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Role</p>
              <p className="text-sm text-gray-900 mt-0.5">{contract.job_position.title}</p>
            </div>
          </div>
          <div className="flex items-start gap-2.5">
            <Building2 className="w-3.5 h-3.5 text-gray-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Department</p>
              <p className="text-sm text-gray-900 mt-0.5">{contract.department.name}</p>
            </div>
          </div>
          <div className="flex items-start gap-2.5">
            <Clock className="w-3.5 h-3.5 text-gray-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Working Schedule</p>
              <p className={`text-sm mt-0.5 ${contract.working_schedule ? 'text-gray-900' : 'text-gray-400 italic'}`}>
                {contract.working_schedule ? `${contract.working_schedule.name} · ${contract.working_schedule.hours_per_week}h/week` : 'Not set'}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 pt-5 border-t border-gray-100">
          <div className="flex items-start gap-2.5">
            <StickyNote className="w-3.5 h-3.5 text-gray-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Notes (Salary Structure — deferred)</p>
              <p className={`text-sm mt-0.5 ${contract.salary_structure_note ? 'text-gray-900' : 'text-gray-400 italic'}`}>
                {contract.salary_structure_note || 'No notes. Salary Structure assignment belongs to a later payroll phase.'}
              </p>
            </div>
          </div>
        </div>
      </SectionCard>
    </div>
  );
}
