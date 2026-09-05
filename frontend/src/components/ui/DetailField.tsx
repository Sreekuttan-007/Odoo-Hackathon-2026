import type { LucideIcon } from 'lucide-react';

interface DetailFieldProps {
  icon?: LucideIcon;
  label: string;
  value?: string | null;
  valueNode?: React.ReactNode;
}

export function DetailField({ icon: Icon, label, value, valueNode }: DetailFieldProps) {
  return (
    <div className="flex items-start gap-3">
      {Icon && (
        <div className="mt-0.5 h-7 w-7 rounded-md bg-gray-50 border border-gray-100 flex items-center justify-center shrink-0">
          <Icon className="w-3.5 h-3.5 text-gray-400" />
        </div>
      )}
      <div className="min-w-0">
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">{label}</p>
        {valueNode ?? (
          <p className={`text-sm mt-0.5 ${value ? 'text-gray-900' : 'text-gray-400 italic'}`}>{value || 'Not set'}</p>
        )}
      </div>
    </div>
  );
}
