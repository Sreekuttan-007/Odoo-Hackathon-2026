import type { ReactNode } from 'react';

interface SectionCardProps {
  children: ReactNode;
  className?: string;
  padded?: boolean;
}

export function SectionCard({ children, className = '', padded = true }: SectionCardProps) {
  return (
    <div className={`bezel ${className}`}>
      <div className={`bezel-core ${padded ? 'p-6' : ''}`}>{children}</div>
    </div>
  );
}
