import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { LogOut } from 'lucide-react';

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const activeClass = "bg-blue-800 text-white";
  const inactiveClass = "text-blue-100 hover:bg-blue-800 hover:text-white";

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 bg-blue-900 flex flex-col transition-all duration-300">
        <div className="flex h-16 shrink-0 items-center px-6">
          <span className="text-xl font-bold text-white tracking-tight">PeoplePay360</span>
        </div>
        
        <nav className="flex flex-1 flex-col overflow-y-auto px-4 py-4 space-y-1">
          <NavLink to="/dashboard" className={({isActive}) => `px-3 py-2 rounded-md text-sm font-medium ${isActive ? activeClass : inactiveClass}`}>Dashboard</NavLink>
          
          <div className="pt-4 pb-1">
            <p className="px-3 text-xs font-semibold text-blue-300 uppercase tracking-wider">Employees</p>
          </div>
          <NavLink to="/employees" className={({isActive}) => `px-3 py-2 rounded-md text-sm font-medium ${isActive ? activeClass : inactiveClass}`}>Employees</NavLink>
          <NavLink to="/contracts" className={({isActive}) => `px-3 py-2 rounded-md text-sm font-medium ${isActive ? activeClass : inactiveClass}`}>Contracts</NavLink>
          <NavLink to="/departments" className={({isActive}) => `px-3 py-2 rounded-md text-sm font-medium ${isActive ? activeClass : inactiveClass}`}>Departments</NavLink>
          <NavLink to="/working-schedules" className={({isActive}) => `px-3 py-2 rounded-md text-sm font-medium ${isActive ? activeClass : inactiveClass}`}>Working Schedules</NavLink>
          
          <div className="pt-4 pb-1">
            <p className="px-3 text-xs font-semibold text-blue-300 uppercase tracking-wider">Time & Attendance</p>
          </div>
          <NavLink to="/attendance" className={({isActive}) => `px-3 py-2 rounded-md text-sm font-medium ${isActive ? activeClass : inactiveClass}`}>Attendance</NavLink>
          <NavLink to="/time-off/requests" className={({isActive}) => `px-3 py-2 rounded-md text-sm font-medium ${isActive ? activeClass : inactiveClass}`}>Time Off Requests</NavLink>
          <NavLink to="/time-off/allocations" className={({isActive}) => `px-3 py-2 rounded-md text-sm font-medium ${isActive ? activeClass : inactiveClass}`}>Allocations</NavLink>
          <NavLink to="/time-off/types" className={({isActive}) => `px-3 py-2 rounded-md text-sm font-medium ${isActive ? activeClass : inactiveClass}`}>Time Off Types</NavLink>
          
          <div className="pt-4 pb-1">
            <p className="px-3 text-xs font-semibold text-blue-300 uppercase tracking-wider">Payroll</p>
          </div>
          <NavLink to="/payroll/payruns" className={({isActive}) => `px-3 py-2 rounded-md text-sm font-medium ${isActive ? activeClass : inactiveClass}`}>Payruns</NavLink>
          <NavLink to="/payroll/payslips" className={({isActive}) => `px-3 py-2 rounded-md text-sm font-medium ${isActive ? activeClass : inactiveClass}`}>Payslips</NavLink>
          <NavLink to="/payroll/salary-structures" className={({isActive}) => `px-3 py-2 rounded-md text-sm font-medium ${isActive ? activeClass : inactiveClass}`}>Salary Structures</NavLink>
          <NavLink to="/payroll/salary-rules" className={({isActive}) => `px-3 py-2 rounded-md text-sm font-medium ${isActive ? activeClass : inactiveClass}`}>Salary Rules</NavLink>
          
          {user?.role === 'ADMIN' && (
            <>
              <div className="pt-4 pb-1">
                <p className="px-3 text-xs font-semibold text-blue-300 uppercase tracking-wider">Administration</p>
              </div>
              <NavLink to="/admin/users" className={({isActive}) => `px-3 py-2 rounded-md text-sm font-medium ${isActive ? activeClass : inactiveClass}`}>Users</NavLink>
            </>
          )}
        </nav>

        {/* User profile */}
        <div className="flex shrink-0 border-t border-blue-800 p-4">
          <div className="flex w-full items-center justify-between">
            <div className="flex items-center truncate mr-2">
              <div className="ml-3 truncate">
                <p className="text-sm font-medium text-white truncate">{user?.employee?.first_name} {user?.employee?.last_name}</p>
                <p className="text-xs font-medium text-blue-200 truncate">{user?.role}</p>
              </div>
            </div>
            <button onClick={handleLogout} className="text-blue-200 hover:text-white p-2">
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-gray-200 bg-white px-6">
          <h1 className="text-lg font-semibold text-gray-900">Workspace</h1>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
