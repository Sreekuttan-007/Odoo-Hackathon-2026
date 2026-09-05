import { useState, useEffect } from 'react';
import api from '../services/api';

export function CreateUserModal({ isOpen, onClose, onCreated }: any) {
  const [employees, setEmployees] = useState<any[]>([]);
  const [formData, setFormData] = useState({
    employee_id: '',
    work_email: '',
    role: 'EMPLOYEE',
    status: 'ACTIVE',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) {
      api.get('/admin/employees/lookup').then(res => setEmployees(res.data));
    }
  }, [isOpen]);

  const handleSubmit = async (e: any) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      await api.post('/admin/users', { ...formData, employee_id: parseInt(formData.employee_id) });
      onCreated();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail?.error?.message || 'Failed to create user');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:p-0">
        <div className="fixed inset-0 transition-opacity" aria-hidden="true">
          <div className="absolute inset-0 bg-gray-500 opacity-75" onClick={onClose}></div>
        </div>

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">Create New User</h3>
            
            {error && <div className="mb-4 text-sm text-red-600 bg-red-50 p-3 rounded-md">{error}</div>}
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Employee</label>
                <select 
                  required
                  value={formData.employee_id}
                  onChange={(e) => {
                    const emp = employees.find(x => x.id === parseInt(e.target.value));
                    setFormData({...formData, employee_id: e.target.value, work_email: emp?.work_email || formData.work_email});
                  }}
                  className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-brand-500 focus:border-brand-500 sm:text-sm rounded-md border"
                >
                  <option value="" disabled>Select Employee</option>
                  {employees.map(emp => (
                    <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name} · {emp.department}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Work Email</label>
                <input 
                  type="email" required
                  value={formData.work_email} onChange={e => setFormData({...formData, work_email: e.target.value})}
                  className="mt-1 focus:ring-brand-500 focus:border-brand-500 block w-full sm:text-sm border-gray-300 rounded-md py-2 px-3 border"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Temporary Password</label>
                <input 
                  type="text" required
                  value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})}
                  className="mt-1 focus:ring-brand-500 focus:border-brand-500 block w-full sm:text-sm border-gray-300 rounded-md py-2 px-3 border"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Role</label>
                <select 
                  value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})}
                  className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-brand-500 focus:border-brand-500 sm:text-sm rounded-md border"
                >
                  <option value="EMPLOYEE">Employee</option>
                  <option value="HR_MANAGER">HR Manager</option>
                  <option value="HR_PAYROLL_USER">HR Payroll User</option>
                  <option value="HR_PAYROLL_MANAGER">HR Payroll Manager</option>
                  <option value="ADMIN">Admin</option>
                </select>
              </div>

              <div className="mt-5 sm:mt-6 sm:flex sm:flex-row-reverse">
                <button type="submit" disabled={loading} className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-brand-600 text-base font-medium text-white hover:bg-brand-700 focus:outline-none sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-70">
                  {loading ? 'Creating...' : 'Create'}
                </button>
                <button type="button" onClick={onClose} className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
