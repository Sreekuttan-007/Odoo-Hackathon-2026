import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import { ArrowRight, Eye, EyeOff, Loader2 } from 'lucide-react';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please enter both email and password.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const res = await api.post('/auth/login', { email, password });
      await login(res.data.access_token);
      navigate('/dashboard');
    } catch (err: any) {
      if (err.response?.data?.detail?.error?.message) {
        setError(err.response.data.detail.error.message);
      } else {
        setError('We couldn\'t sign you in right now. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-white">
      {/* Brand panel */}
      <div
        className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 relative overflow-hidden"
        style={{
          background:
            'radial-gradient(120% 100% at 0% 100%, rgb(20 122 92 / 0.35), transparent 55%), radial-gradient(80% 60% at 100% 0%, rgb(20 122 92 / 0.18), transparent 60%), #0d1210',
        }}
      >
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              'linear-gradient(rgb(255 255 255) 1px, transparent 1px), linear-gradient(90deg, rgb(255 255 255) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />

        <div className="relative flex items-center gap-2.5">
          <div className="h-7 w-7 rounded-lg bg-brand-500 flex items-center justify-center shadow-[0_2px_10px_-1px_rgb(20,122,92,0.6)]">
            <span className="text-white text-sm font-bold font-display">P</span>
          </div>
          <span className="text-white text-lg font-bold tracking-tight font-display">Payloom</span>
        </div>
        <div className="relative">
          <span className="eyebrow bg-white/10 text-brand-200 mb-4">People · Time · Payroll</span>
          <p className="text-3xl font-bold text-white leading-[1.15] max-w-sm font-display">
            HR &amp; Payroll, woven together.
          </p>
          <p className="text-sm text-gray-400 mt-4 max-w-sm">
            Employees, contracts, schedules and payroll — one connected record
            of truth for your workforce.
          </p>
        </div>
        <p className="relative text-xs text-gray-500">© 2026 Payloom</p>
      </div>

      {/* Form panel */}
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-2.5 mb-10">
            <div className="h-7 w-7 rounded-lg bg-brand-600 flex items-center justify-center">
              <span className="text-white text-sm font-bold font-display">P</span>
            </div>
            <span className="text-gray-900 text-lg font-bold tracking-tight font-display">Payloom</span>
          </div>

          <h1 className="text-2xl font-bold text-gray-900 font-display">Welcome back</h1>
          <p className="text-sm text-gray-500 mt-1 mb-8">Sign in to your workspace.</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-md bg-red-50 border border-red-100 px-3 py-2.5">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-xs font-medium text-gray-600 mb-1.5">
                Work email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="block w-full h-10 px-3.5 rounded-lg border border-gray-300 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
                placeholder="you@company.com"
                disabled={loading}
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="password" className="block text-xs font-medium text-gray-600">
                  Password
                </label>
              </div>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full h-10 px-3.5 pr-10 rounded-lg border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                  disabled={loading}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-pill-cta w-full justify-between mt-2">
              Sign in
              <span className="btn-pill-cta-icon">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
              </span>
            </button>

            <p className="text-center text-xs text-gray-400 pt-2">
              Accounts are created by an administrator.
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
