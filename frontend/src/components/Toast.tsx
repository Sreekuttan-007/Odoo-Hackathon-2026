import { useState, useCallback } from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';

interface ToastState {
  id: number;
  message: string;
  variant: 'success' | 'error';
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastState[]>([]);

  const push = useCallback((message: string, variant: 'success' | 'error' = 'success') => {
    const id = Date.now() + Math.random();
    setToasts(t => [...t, { id, message, variant }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3500);
  }, []);

  return { toasts, push };
}

export function ToastViewport({ toasts }: { toasts: ToastState[] }) {
  return (
    <div className="fixed bottom-6 right-6 z-50 space-y-2">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`flex items-center gap-2 rounded-lg shadow-[var(--shadow-popover)] px-4 py-3 text-sm font-medium border transition-all duration-150 ${
            t.variant === 'success' ? 'bg-white border-green-200 text-green-800' : 'bg-white border-red-200 text-red-800'
          }`}
        >
          {t.variant === 'success' ? <CheckCircle2 className="w-4 h-4 text-green-500" /> : <XCircle className="w-4 h-4 text-red-500" />}
          {t.message}
        </div>
      ))}
    </div>
  );
}
