import type { ReactNode } from 'react';
import { X } from 'lucide-react';

interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function Drawer({ isOpen, onClose, title, children, footer }: DrawerProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div className="fixed inset-0 bg-gray-900/30 transition-opacity" onClick={onClose} />
      <div className="fixed inset-y-0 right-0 flex max-w-full">
        <div className="w-screen max-w-md bg-white shadow-[var(--shadow-popover)] flex flex-col h-full animate-[drawer-in_0.18s_ease-out]">
          <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4 shrink-0">
            <h3 className="text-base font-semibold text-gray-900">{title}</h3>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 rounded-md p-1 hover:bg-gray-100 transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
          {footer && <div className="border-t border-gray-100 px-6 py-4 shrink-0">{footer}</div>}
        </div>
      </div>
      <style>{`
        @keyframes drawer-in {
          from { transform: translateX(16px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
