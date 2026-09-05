import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/AppShell';

// Placeholder Pages
const Dashboard = () => <div className="page-title">Dashboard</div>;
const Employees = () => <div className="page-title">Employees</div>;
const Contracts = () => <div className="page-title">Contracts</div>;
const Schedules = () => <div className="page-title">Working Schedules</div>;
const Attendance = () => <div className="page-title">Attendance</div>;
const TimeOffRequests = () => <div className="page-title">Time Off Requests</div>;
const TimeOffAllocations = () => <div className="page-title">Time Off Allocations</div>;
const TimeOffTypes = () => <div className="page-title">Time Off Types</div>;
const Payruns = () => <div className="page-title">Payruns</div>;
const Payslips = () => <div className="page-title">Payslips</div>;
const SalaryStructures = () => <div className="page-title">Salary Structures</div>;
const SalaryRules = () => <div className="page-title">Salary Rules</div>;
const Users = () => <div className="page-title">Users</div>;
const Roles = () => <div className="page-title">Roles</div>;

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          
          <Route path="employees" element={<Employees />} />
          <Route path="contracts" element={<Contracts />} />
          <Route path="schedules" element={<Schedules />} />
          
          <Route path="attendance" element={<Attendance />} />
          
          <Route path="time-off/requests" element={<TimeOffRequests />} />
          <Route path="time-off/allocations" element={<TimeOffAllocations />} />
          <Route path="time-off/types" element={<TimeOffTypes />} />
          
          <Route path="payroll/payruns" element={<Payruns />} />
          <Route path="payroll/payslips" element={<Payslips />} />
          <Route path="payroll/salary-structures" element={<SalaryStructures />} />
          <Route path="payroll/salary-rules" element={<SalaryRules />} />
          
          <Route path="reports/payroll" element={<Dashboard />} />
          
          <Route path="admin/users" element={<Users />} />
          <Route path="admin/roles" element={<Roles />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
