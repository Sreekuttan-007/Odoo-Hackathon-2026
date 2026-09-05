import type { ReactNode } from 'react';

interface SectionCardProps {
  children: ReactNode;
  className?: string;
  padded?: boolean;
}

export function SectionCard({ children, className = '', padded = true }: SectionCardProps) {
  return (
    <div className={`rounded-xl border border-gray-200 bg-white shadow-[var(--shadow-elevation)] ${padded ? 'p-6' : ''} ${className}`}>
      {children}
    </div>
  );
}
