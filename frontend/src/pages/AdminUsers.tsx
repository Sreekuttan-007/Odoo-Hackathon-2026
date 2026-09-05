import { useState, useEffect } from 'react';
import api from '../services/api';
import type { User } from '../contexts/AuthContext';
import { Search, Plus, Edit2, Shield, UserX, UserCheck } from 'lucide-react';
import { UserFormDrawer } from '../components/UserFormDrawer';
import { StatusBadge } from '../components/StatusBadge';
import { PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { SkeletonTable } from '../components/ui/Skeleton';
import { useToast, ToastViewport } from '../components/Toast';
import { Users } from 'lucide-react';

export function AdminUsers() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const { toasts, push } = useToast();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);

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
      push("Couldn't load users. Your data wasn't changed.", 'error');
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
      push(newStatus === 'ACTIVE' ? 'Account activated.' : 'Account deactivated.');
    } catch (err) {
      console.error(err);
      push('Failed to update status.', 'error');
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader
        title="User Management"
        description="Manage login accounts, employee links, roles and access."
        action={
          <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
            <Plus className="w-4 h-4" /> New User
          </Button>
        }
      />

      <div className="bg-white rounded-xl border border-gray-200 shadow-[var(--shadow-elevation)]">
        <div className="p-3.5 border-b border-gray-100 flex flex-col sm:flex-row gap-3 items-center justify-between">
          <div className="relative w-full sm:w-96">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-3.5 w-3.5 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Search users, employees or email…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="block w-full h-9 pl-9 pr-3 border border-gray-300 rounded-md bg-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 text-sm"
            />
          </div>

          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="w-full sm:w-56 h-9 rounded-md border border-gray-300 px-2.5 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500"
          >
            <option value="">All Roles</option>
            <option value="ADMIN">Admin</option>
            <option value="HR_MANAGER">HR Manager</option>
            <option value="HR_PAYROLL_MANAGER">HR Payroll Manager</option>
            <option value="HR_PAYROLL_USER">HR Payroll User</option>
            <option value="EMPLOYEE">Employee</option>
          </select>
        </div>

        {loading ? (
          <SkeletonTable rows={5} cols={4} />
        ) : users.length === 0 ? (
          <EmptyState icon={Users} title="No users match your search or filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Employee</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Work Email</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Role</th>
                  <th className="px-6 py-2.5 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-2.5 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-3 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="h-8 w-8 flex-shrink-0 bg-brand-50 rounded-full flex items-center justify-center text-brand-700 font-semibold text-xs">
                          {user.employee?.first_name?.[0]}{user.employee?.last_name?.[0]}
                        </div>
                        <div className="ml-3">
                          <div className="text-sm font-medium text-gray-900">{user.employee?.first_name} {user.employee?.last_name}</div>
                          <div className="text-xs text-gray-400">Employee ID: {user.employee_id}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">{user.work_email}</td>
                    <td className="px-6 py-3 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-600">
                        <Shield className="w-3.5 h-3.5 mr-1.5 text-gray-400" />
                        {user.role.replace(/_/g, ' ')}
                      </div>
                    </td>
                    <td className="px-6 py-3 whitespace-nowrap"><StatusBadge status={user.status} /></td>
                    <td className="px-6 py-3 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => setEditingUser(user)}
                        className="text-gray-400 hover:text-brand-600 mr-3 transition-colors"
                        title="Edit"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => toggleStatus(user)}
                        className={`transition-colors ${user.status === 'ACTIVE' ? 'text-gray-400 hover:text-danger-600' : 'text-gray-400 hover:text-brand-600'}`}
                        title={user.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                      >
                        {user.status === 'ACTIVE' ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <UserFormDrawer
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSaved={() => { fetchUsers(); push('User created.'); }}
      />
      <UserFormDrawer
        isOpen={!!editingUser}
        user={editingUser}
        onClose={() => setEditingUser(null)}
        onSaved={() => { fetchUsers(); push('User updated.'); }}
      />
      <ToastViewport toasts={toasts} />
    </div>
  );
}
