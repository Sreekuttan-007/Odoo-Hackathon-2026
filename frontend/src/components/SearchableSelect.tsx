import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check, Plus, X } from 'lucide-react';

export interface SelectOption {
  id: number;
  label: string;
  sublabel?: string;
}

interface SearchableSelectProps {
  options: SelectOption[];
  value: number | null;
  onChange: (id: number | null) => void;
  placeholder?: string;
  clearable?: boolean;
  disabled?: boolean;
  onCreate?: (name: string) => Promise<SelectOption>;
  createLabel?: string;
}

export function SearchableSelect({
  options, value, onChange, placeholder = 'Select…', clearable = true, disabled = false, onCreate, createLabel = 'Create',
}: SearchableSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [creating, setCreating] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selected = options.find(o => o.id === value) || null;

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setQuery('');
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const filtered = options.filter(o => o.label.toLowerCase().includes(query.toLowerCase()));
  const exactMatch = options.some(o => o.label.toLowerCase() === query.trim().toLowerCase());

  const handleCreate = async () => {
    if (!onCreate || !query.trim()) return;
    setCreating(true);
    try {
      const created = await onCreate(query.trim());
      onChange(created.id);
      setOpen(false);
      setQuery('');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen(o => !o)}
        className="flex h-9 w-full items-center justify-between rounded-md border border-gray-300 bg-white px-3 text-sm text-left focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 disabled:bg-gray-50 disabled:text-gray-400"
      >
        <span className={selected ? 'text-gray-900' : 'text-gray-400'}>
          {selected ? selected.label : placeholder}
        </span>
        <div className="flex items-center gap-1">
          {clearable && selected && (
            <span
              role="button"
              onClick={(e) => { e.stopPropagation(); onChange(null); }}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-3.5 h-3.5" />
            </span>
          )}
          <ChevronDown className="w-4 h-4 text-gray-400" />
        </div>
      </button>

      {open && !disabled && (
        <div className="absolute z-20 mt-1 w-full rounded-md border border-gray-200 bg-white shadow-lg">
          <div className="p-2 border-b border-gray-100">
            <input
              autoFocus
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search…"
              className="w-full rounded border border-gray-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <div className="max-h-56 overflow-y-auto py-1">
            {filtered.length === 0 && !onCreate && (
              <div className="px-3 py-2 text-sm text-gray-400">No matches.</div>
            )}
            {filtered.map(opt => (
              <button
                type="button"
                key={opt.id}
                onClick={() => { onChange(opt.id); setOpen(false); setQuery(''); }}
                className="flex w-full items-center justify-between px-3 py-2 text-sm text-left hover:bg-brand-50"
              >
                <span>
                  {opt.label}
                  {opt.sublabel && <span className="text-gray-400 ml-1.5">· {opt.sublabel}</span>}
                </span>
                {opt.id === value && <Check className="w-4 h-4 text-brand-600" />}
              </button>
            ))}
            {onCreate && query.trim() && !exactMatch && (
              <button
                type="button"
                disabled={creating}
                onClick={handleCreate}
                className="flex w-full items-center gap-1.5 px-3 py-2 text-sm text-left text-brand-700 hover:bg-brand-50 border-t border-gray-100"
              >
                <Plus className="w-3.5 h-3.5" />
                {creating ? 'Creating…' : `${createLabel} "${query.trim()}"`}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
