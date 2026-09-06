import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { AlertTriangle } from 'lucide-react';
import { Button } from './Button';

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * A deliberate, hard-to-misclick confirmation modal — used in place of the
 * browser's native `confirm()` for actions where a stray click has a real
 * cost (e.g. ending an attendance session early). The backdrop blur removes
 * all visual context from the page behind it, and the card's brief shake on
 * entrance is a physical "pay attention" cue before the user reads on.
 */
export function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onCancel();
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div
        className="fixed inset-0 bg-gray-900/50 backdrop-blur-sm animate-[confirm-backdrop-in_0.15s_ease-out]"
        onClick={onCancel}
      />
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        className="relative w-full max-w-sm rounded-2xl bg-white shadow-[var(--shadow-popover)] p-6 animate-[confirm-pop-in_0.4s_cubic-bezier(0.36,0.07,0.19,0.97)]"
      >
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-warning-50 text-warning-600">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div className="min-w-0 pt-0.5">
            <h3 id="confirm-dialog-title" className="text-base font-semibold text-gray-900 font-display">
              {title}
            </h3>
            <p className="mt-1.5 text-sm leading-relaxed text-gray-500 whitespace-pre-line">{message}</p>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2.5">
          <Button variant="secondary" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button variant="destructive" onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </div>
      </div>
      <style>{`
        @keyframes confirm-backdrop-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes confirm-pop-in {
          0%   { transform: scale(0.92) translateX(0); opacity: 0; }
          45%  { transform: scale(1.01) translateX(0); opacity: 1; }
          58%  { transform: scale(1) translateX(-6px); }
          70%  { transform: scale(1) translateX(4px); }
          82%  { transform: scale(1) translateX(-2px); }
          92%  { transform: scale(1) translateX(1px); }
          100% { transform: scale(1) translateX(0); opacity: 1; }
        }
        @media (prefers-reduced-motion: reduce) {
          [role="alertdialog"] { animation: none !important; }
        }
      `}</style>
    </div>,
    document.body,
  );
}
