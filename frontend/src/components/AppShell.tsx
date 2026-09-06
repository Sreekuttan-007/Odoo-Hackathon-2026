import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { AttendanceWidget } from './AttendanceWidget';
import { LogOut, LayoutDashboard, Users, FileText, Building2, Clock, CalendarCheck, PlaneTakeoff, Wallet, ShieldCheck, FlaskConical } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { Role } from '../types';
import logoDark from '../assets/logo-dark.png';

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  roles?: Role[];
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const HR_ROLES: Role[] = ['HR_MANAGER', 'HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];
const PAYROLL_OPERATOR_ROLES: Role[] = ['HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN'];
const PAYROLL_CONFIG_ROLES: Role[] = ['HR_PAYROLL_MANAGER', 'ADMIN'];

const NAV_GROUPS: NavGroup[] = [
  { label: '', items: [{ to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard }] },
  {
    label: 'People',
    items: [
      { to: '/employees', label: 'Employees', icon: Users },
      { to: '/contracts', label: 'Contracts', icon: FileText },
      { to: '/departments', label: 'Departments', icon: Building2, roles: HR_ROLES },
      { to: '/working-schedules', label: 'Working Schedules', icon: Clock, roles: HR_ROLES },
    ],
  },
  {
    label: 'Time & Attendance',
    items: [
      { to: '/attendance', label: 'Attendance', icon: CalendarCheck },
      { to: '/time-off/requests', label: 'Time Off Requests', icon: PlaneTakeoff },
      { to: '/time-off/allocations', label: 'Allocations', icon: PlaneTakeoff, roles: HR_ROLES },
      { to: '/time-off/types', label: 'Time Off Types', icon: PlaneTakeoff, roles: HR_ROLES },
    ],
  },
  {
    label: 'Payroll',
    items: [
      { to: '/payroll/payruns', label: 'Payruns', icon: Wallet, roles: PAYROLL_OPERATOR_ROLES },
      { to: '/payroll/payslips', label: 'Payslips', icon: Wallet },
      { to: '/payroll/salary-structures', label: 'Salary Structures', icon: Wallet, roles: PAYROLL_OPERATOR_ROLES },
      { to: '/payroll/salary-rules', label: 'Salary Rules', icon: Wallet, roles: PAYROLL_OPERATOR_ROLES },
      { to: '/payroll/simulator', label: 'Simulator', icon: FlaskConical, roles: PAYROLL_CONFIG_ROLES },
    ],
  },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const visibleGroups = NAV_GROUPS
    .map(group => ({
      ...group,
      items: group.items.filter(item => !item.roles || (user && item.roles.includes(user.role))),
    }))
    .filter(group => group.items.length > 0);

  const pageTitle = NAV_GROUPS.flatMap(g => g.items).find(item => location.pathname.startsWith(item.to))?.label
    || (location.pathname.startsWith('/admin') ? 'Users' : 'Workspace');

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-60 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col">
        <div className="flex h-14 shrink-0 items-center px-5 border-b border-gray-100">
          <img src={logoDark} alt="Payloom" className="h-6 w-auto" />
        </div>

        <nav className="flex flex-1 flex-col overflow-y-auto px-3 py-4 space-y-5">
          {visibleGroups.map((group, i) => (
            <div key={i}>
              {group.label && (
                <p className="px-3 mb-1.5 text-[11px] font-semibold text-gray-400 uppercase tracking-wider">{group.label}</p>
              )}
              <div className="space-y-0.5">
                {group.items.map(item => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    data-active={location.pathname.startsWith(item.to)}
                    className={({ isActive }) =>
                      `nav-link flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[13px] transition-colors duration-150 ${
                        isActive
                          ? 'bg-brand-50 text-brand-700 font-semibold'
                          : 'text-gray-600 font-medium hover:bg-gray-50 hover:text-gray-900'
                      }`
                    }
                  >
                    <item.icon className="w-4 h-4 shrink-0 transition-transform duration-150" />
                    <span className="truncate">{item.label}</span>
                  </NavLink>
                ))}
              </div>
            </div>
          ))}

          {user?.role === 'ADMIN' && (
            <div>
              <p className="px-3 mb-1.5 text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Administration</p>
              <NavLink
                to="/admin/users"
                data-active={location.pathname.startsWith('/admin/users')}
                className={({ isActive }) =>
                  `nav-link flex items-center gap-2.5 px-3 py-1.5 rounded-md text-[13px] font-medium transition-colors duration-150 ${
                    isActive ? 'bg-brand-50 text-brand-700' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`
                }
              >
                <ShieldCheck className="w-4 h-4 shrink-0" />
                Users
              </NavLink>
            </div>
          )}
        </nav>

        {/* User profile */}
        <div className="flex shrink-0 border-t border-gray-100 p-3">
          <div className="flex w-full items-center justify-between px-2">
            <div className="flex items-center gap-2.5 truncate">
              <div className="h-7 w-7 rounded-full bg-brand-50 flex items-center justify-center text-brand-700 text-xs font-semibold shrink-0">
                {user?.employee?.first_name?.[0]}{user?.employee?.last_name?.[0]}
              </div>
              <div className="truncate">
                <p className="text-[13px] font-medium text-gray-900 truncate">{user?.employee?.first_name} {user?.employee?.last_name}</p>
                <p className="text-[11px] text-gray-400 truncate">{user?.role.replace(/_/g, ' ')}</p>
              </div>
            </div>
            <button onClick={handleLogout} title="Log out" className="text-gray-400 hover:text-gray-700 p-1.5 rounded-md hover:bg-gray-100 transition-colors">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-gray-200 bg-white px-6">
          <h2 className="text-[13px] font-semibold text-gray-500 uppercase tracking-wider">{pageTitle}</h2>
          <AttendanceWidget />
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          <div key={location.pathname} className="page-transition">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
