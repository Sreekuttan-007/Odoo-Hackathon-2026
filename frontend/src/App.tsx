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

// Placeholder Pages
const Placeholder = ({ title }: { title: string }) => (
  <div className="flex h-full flex-col items-center justify-center rounded-xl border border-dashed border-gray-200 p-12 text-center">
    <h2 className="text-base font-semibold text-gray-700 mb-1.5">{title}</h2>
    <p className="text-sm text-gray-500">Coming in a future phase.</p>
  </div>
);

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<AppShell />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Placeholder title="Dashboard" />} />
            
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
              <Route path="payruns" element={<Placeholder title="Payruns" />} />
              <Route path="payslips" element={<Placeholder title="Payslips" />} />
              <Route path="salary-structures" element={<Placeholder title="Salary Structures" />} />
              <Route path="salary-rules" element={<Placeholder title="Salary Rules" />} />
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

