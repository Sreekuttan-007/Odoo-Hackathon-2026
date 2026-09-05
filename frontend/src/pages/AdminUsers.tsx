import { useState, useEffect } from 'react';
import api from '../services/api';
import type { User } from '../contexts/AuthContext';
import type { Role } from '../types';
import { Search, Plus, Edit2, Shield, UserX, UserCheck, Loader2 } from 'lucide-react';
import { CreateUserModal } from '../components/CreateUserModal';

export function AdminUsers() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  
  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (roleFilter) params.append('role', roleFilter);
      
      const res = await api.get('/admin/users', { params });
      setUsers(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      fetchUsers();
    }, 300);
    return () => clearTimeout(delayDebounce);
  }, [search, roleFilter]);

  const toggleStatus = async (user: User) => {
    if (user.status === 'ACTIVE') {
      if (!confirm(`Deactivate ${user.employee?.first_name}'s account?\nThey will no longer be able to sign in.`)) return;
    }
    
    try {
      const newStatus = user.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
      await api.put(`/admin/users/${user.id}`, { status: newStatus });
      fetchUsers();
    } catch (err) {
      console.error(err);
      alert('Failed to update status');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 tracking-tight">User Management</h2>
          <p className="text-sm text-gray-500 mt-1">Manage login accounts, employee links, roles and access.</p>
        </div>
        <button 
          onClick={() => setIsCreateOpen(true)}
          className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-brand-600 hover:bg-brand-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          New User
        </button>
      </div>

      <div className="bg-white shadow rounded-lg border border-gray-200">
        <div className="p-4 border-b border-gray-200 flex flex-col sm:flex-row gap-4 items-center justify-between">
          <div className="relative w-full sm:w-96">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Search users, employees or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-brand-500 focus:border-brand-500 sm:text-sm"
            />
          </div>
          
          <div className="w-full sm:w-64">
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-brand-500 focus:border-brand-500 sm:text-sm rounded-md border"
            >
              <option value="">All Roles</option>
              <option value="ADMIN">Admin</option>
              <option value="HR_MANAGER">HR Manager</option>
              <option value="HR_PAYROLL_MANAGER">HR Payroll Manager</option>
              <option value="HR_PAYROLL_USER">HR Payroll User</option>
              <option value="EMPLOYEE">Employee</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Employee</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Work Email</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <Loader2 className="w-8 h-8 animate-spin mx-auto text-brand-500" />
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                    No users match your search or filters.
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="h-10 w-10 flex-shrink-0 bg-brand-100 rounded-full flex items-center justify-center text-brand-600 font-bold">
                          {user.employee?.first_name?.[0]}{user.employee?.last_name?.[0]}
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">{user.employee?.first_name} {user.employee?.last_name}</div>
                          <div className="text-sm text-gray-500">Employee ID: {user.employee_id}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{user.work_email}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-700">
                        <Shield className="w-4 h-4 mr-1.5 text-gray-400" />
                        {user.role}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2.5 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        user.status === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {user.status === 'ACTIVE' ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button 
                        onClick={() => { alert('Edit not implemented in Phase 1 MVP') }}
                        className="text-brand-600 hover:text-brand-900 mr-4"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button 
                        onClick={() => toggleStatus(user)}
                        className={`${user.status === 'ACTIVE' ? 'text-red-600 hover:text-red-900' : 'text-green-600 hover:text-green-900'}`}
                        title={user.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                      >
                        {user.status === 'ACTIVE' ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      
      <CreateUserModal 
        isOpen={isCreateOpen} 
        onClose={() => setIsCreateOpen(false)} 
        onCreated={() => { fetchUsers(); }} 
      />
    </div>
  );
}
