import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Users, 
  FileText, 
  CalendarDays, 
  Clock, 
  Calendar, 
  Umbrella, 
  Briefcase, 
  FileSignature, 
  Calculator, 
  DollarSign,
  Settings,
  Shield
} from 'lucide-react';

const Sidebar = () => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        PeoplePay360
      </div>
      <nav className="sidebar-nav">
        
        <div className="nav-section">
          <div className="nav-section-title">Dashboard</div>
          <NavLink to="/dashboard" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <LayoutDashboard size={18} style={{marginRight: '12px'}} />
            Overview
          </NavLink>
        </div>

        <div className="nav-section">
          <div className="nav-section-title">Employees</div>
          <NavLink to="/employees" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <Users size={18} style={{marginRight: '12px'}} />
            Employees
          </NavLink>
          <NavLink to="/contracts" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <FileText size={18} style={{marginRight: '12px'}} />
            Contracts
          </NavLink>
          <NavLink to="/schedules" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <CalendarDays size={18} style={{marginRight: '12px'}} />
            Working Schedules
          </NavLink>
        </div>

        <div className="nav-section">
          <div className="nav-section-title">Attendance</div>
          <NavLink to="/attendance" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <Clock size={18} style={{marginRight: '12px'}} />
            Attendance
          </NavLink>
        </div>

        <div className="nav-section">
          <div className="nav-section-title">Time Off</div>
          <NavLink to="/time-off/requests" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <Calendar size={18} style={{marginRight: '12px'}} />
            Requests
          </NavLink>
          <NavLink to="/time-off/allocations" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <Umbrella size={18} style={{marginRight: '12px'}} />
            Allocations
          </NavLink>
          <NavLink to="/time-off/types" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <Briefcase size={18} style={{marginRight: '12px'}} />
            Time Off Types
          </NavLink>
        </div>

        <div className="nav-section">
          <div className="nav-section-title">Payroll</div>
          <NavLink to="/payroll/payruns" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <Calculator size={18} style={{marginRight: '12px'}} />
            Payruns
          </NavLink>
          <NavLink to="/payroll/payslips" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <FileSignature size={18} style={{marginRight: '12px'}} />
            Payslips
          </NavLink>
          <NavLink to="/payroll/salary-structures" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <DollarSign size={18} style={{marginRight: '12px'}} />
            Salary Structures
          </NavLink>
          <NavLink to="/payroll/salary-rules" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <Settings size={18} style={{marginRight: '12px'}} />
            Salary Rules
          </NavLink>
        </div>

        <div className="nav-section">
          <div className="nav-section-title">Reports</div>
          <NavLink to="/reports/payroll" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <LayoutDashboard size={18} style={{marginRight: '12px'}} />
            Payroll Dashboard
          </NavLink>
        </div>

        <div className="nav-section">
          <div className="nav-section-title">Admin</div>
          <NavLink to="/admin/users" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <Users size={18} style={{marginRight: '12px'}} />
            Users
          </NavLink>
          <NavLink to="/admin/roles" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
            <Shield size={18} style={{marginRight: '12px'}} />
            Roles
          </NavLink>
        </div>

      </nav>
    </aside>
  );
};

const Topbar = () => {
  return (
    <header className="topbar">
      <div className="topbar-left">
        {/* Placeholder for breadcrumbs or title */}
      </div>
      <div className="topbar-right">
        <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>Admin User</span>
        <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: 'var(--primary)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.875rem', fontWeight: 'bold' }}>
          AU
        </div>
      </div>
    </header>
  );
};

export const AppShell = () => {
  return (
    <div className="app-container">
      <Sidebar />
      <main className="main-content">
        <Topbar />
        <div className="page-container">
          <Outlet />
        </div>
      </main>
    </div>
  );
};
