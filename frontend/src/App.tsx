import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AuthProvider } from './contexts/AuthContext';
import { Login } from './pages/Login';
import { AdminUsers } from './pages/AdminUsers';

// Placeholder Pages
const Placeholder = ({ title }: { title: string }) => (
  <div className="flex h-full flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
    <h2 className="text-2xl font-semibold text-gray-700 mb-2">{title}</h2>
    <p className="text-gray-500">This module has not been implemented yet in the current phase.</p>
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
            
            <Route path="employees" element={<Placeholder title="Employees" />} />
            <Route path="contracts" element={<Placeholder title="Contracts" />} />
            <Route path="departments" element={<Placeholder title="Departments" />} />
            <Route path="working-schedules" element={<Placeholder title="Working Schedules" />} />
            
            <Route path="attendance" element={<Placeholder title="Attendance" />} />
            
            <Route path="time-off">
              <Route path="requests" element={<Placeholder title="Time Off Requests" />} />
              <Route path="allocations" element={<Placeholder title="Time Off Allocations" />} />
              <Route path="types" element={<Placeholder title="Time Off Types" />} />
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

