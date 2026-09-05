import { Outlet, NavLink } from 'react-router-dom';

export function AppShell() {
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
          
          <div className="pt-4 pb-1">
            <p className="px-3 text-xs font-semibold text-blue-300 uppercase tracking-wider">Administration</p>
          </div>
          <NavLink to="/admin/users" className={({isActive}) => `px-3 py-2 rounded-md text-sm font-medium ${isActive ? activeClass : inactiveClass}`}>Users</NavLink>
        </nav>

        {/* User profile placeholder */}
        <div className="flex shrink-0 border-t border-blue-800 p-4">
          <div className="flex items-center">
            <div className="ml-3">
              <p className="text-sm font-medium text-white">Mock User</p>
              <p className="text-xs font-medium text-blue-200">Admin</p>
            </div>
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
