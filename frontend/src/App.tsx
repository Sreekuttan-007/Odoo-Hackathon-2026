import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AuthProvider } from './contexts/AuthContext';
import { Login } from './pages/Login';
import { AdminUsers } from './pages/AdminUsers';
import { Employees } from './pages/Employees';
import { EmployeeDetail } from './pages/EmployeeDetail';
import { Contracts } from './pages/Contracts';
import { ContractDetail } from './pages/ContractDetail';
import { Departments } from './pages/Departments';
import { WorkingSchedules } from './pages/WorkingSchedules';
import { WorkingScheduleForm } from './pages/WorkingScheduleForm';
import { AttendancePage } from './pages/Attendance';
import { AttendanceDetail } from './pages/AttendanceDetail';
import { TimeOffTypes } from './pages/TimeOffTypes';
import { TimeOffTypeDetail } from './pages/TimeOffTypeDetail';
import { Allocations } from './pages/Allocations';
import { AllocationDetail } from './pages/AllocationDetail';
import { TimeOffRequests } from './pages/TimeOffRequests';
import { TimeOffRequestDetail } from './pages/TimeOffRequestDetail';
import { SalaryStructures } from './pages/SalaryStructures';
import { SalaryStructureDetail } from './pages/SalaryStructureDetail';
import { SalaryRules } from './pages/SalaryRules';
import { Payruns } from './pages/Payruns';
import { PayrunWizard } from './pages/PayrunWizard';
import { PayrunDetail } from './pages/PayrunDetail';
import { Payslips } from './pages/Payslips';
import { PayslipDetail } from './pages/PayslipDetail';
import { Dashboard } from './pages/Dashboard';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<AppShell />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
            
            <Route path="employees" element={<Employees />} />
            <Route path="employees/:employeeId" element={<EmployeeDetail />} />
            <Route path="contracts" element={<Contracts />} />
            <Route path="contracts/:contractId" element={<ContractDetail />} />
            <Route path="departments" element={<Departments />} />
            <Route path="working-schedules" element={<WorkingSchedules />} />
            <Route path="working-schedules/new" element={<WorkingScheduleForm />} />
            <Route path="working-schedules/:scheduleId" element={<WorkingScheduleForm />} />
            
            <Route path="attendance" element={<AttendancePage />} />
            <Route path="attendance/:attendanceId" element={<AttendanceDetail />} />
            
            <Route path="time-off">
              <Route path="requests" element={<TimeOffRequests />} />
              <Route path="requests/:requestId" element={<TimeOffRequestDetail />} />
              <Route path="allocations" element={<Allocations />} />
              <Route path="allocations/:allocationId" element={<AllocationDetail />} />
              <Route path="types" element={<TimeOffTypes />} />
              <Route path="types/:typeId" element={<TimeOffTypeDetail />} />
            </Route>
            
            <Route path="payroll">
              <Route path="payslips" element={<Payslips />} />
              <Route path="payslips/:payslipId" element={<PayslipDetail />} />

              <Route element={<ProtectedRoute allowedRoles={['HR_PAYROLL_USER', 'HR_PAYROLL_MANAGER', 'ADMIN']} />}>
                <Route path="payruns" element={<Payruns />} />
                <Route path="payruns/new" element={<PayrunWizard />} />
                <Route path="payruns/:payrunId" element={<PayrunDetail />} />
                <Route path="salary-structures" element={<SalaryStructures />} />
                <Route path="salary-structures/:structureId" element={<SalaryStructureDetail />} />
                <Route path="salary-rules" element={<SalaryRules />} />
              </Route>
            </Route>
            
            <Route path="admin" element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
              <Route path="users" element={<AdminUsers />} />
            </Route>
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;

