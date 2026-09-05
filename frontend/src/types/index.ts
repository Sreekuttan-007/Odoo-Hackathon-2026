export type Role =
  | 'EMPLOYEE'
  | 'HR_MANAGER'
  | 'HR_PAYROLL_USER'
  | 'HR_PAYROLL_MANAGER'
  | 'ADMIN';

export type AccountStatus = 'ACTIVE' | 'INACTIVE';

export type EmployeeStatus = 'ACTIVE' | 'INACTIVE';

export type ScheduleStatus = 'ACTIVE' | 'INACTIVE';

export type ContractStatus = 'RUNNING' | 'UPCOMING' | 'EXPIRED';

export type AttendanceStatus = 'ACTIVE' | 'MISSING_CHECKOUT' | 'COMPLETED';

export type TimeOffUnit = 'DAYS' | 'HOURS';
export type ApprovalPolicy = 'NONE' | 'MANAGER' | 'HR';
export type AllocationStatus = 'DRAFT' | 'TO_APPROVE' | 'APPROVED' | 'REFUSED';
export type TimeOffRequestStatus = 'TO_APPROVE' | 'APPROVED' | 'REFUSED';

export type DayOfWeek =
  | 'MONDAY'
  | 'TUESDAY'
  | 'WEDNESDAY'
  | 'THURSDAY'
  | 'FRIDAY'
  | 'SATURDAY'
  | 'SUNDAY';

export const DAYS_OF_WEEK: DayOfWeek[] = [
  'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY',
];

export interface Department {
  id: number;
  name: string;
  created_at: string;
  updated_at: string | null;
}

export interface JobPosition {
  id: number;
  title: string;
  created_at: string;
  updated_at: string | null;
}

export interface WorkingScheduleLine {
  id: number;
  day_of_week: DayOfWeek;
  start_time: string;
  end_time: string;
  break_minutes: number;
  derived_hours: number;
}

export interface WorkingScheduleSummary {
  id: number;
  name: string;
  company: string;
  status: ScheduleStatus;
  days_per_week: number;
  hours_per_week: number;
}

export interface WorkingSchedule {
  id: number;
  name: string;
  company: string;
  timezone: string;
  status: ScheduleStatus;
  lines: WorkingScheduleLine[];
  days_per_week: number;
  hours_per_week: number;
  created_at: string;
  updated_at: string | null;
}

export interface EmployeeMinimal {
  id: number;
  first_name: string;
  last_name: string;
  work_email: string | null;
}

export interface Employee {
  id: number;
  employee_code: string | null;
  first_name: string;
  last_name: string;
  work_email: string | null;
  work_location: string | null;
  status: EmployeeStatus;
  department_id: number | null;
  job_position_id: number | null;
  manager_id: number | null;
  working_schedule_id: number | null;
  department: Department | null;
  job_position: JobPosition | null;
  manager: EmployeeMinimal | null;
  working_schedule: WorkingScheduleSummary | null;
  contracts_count: number;
  attendance_count: number;
  time_off_requests_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface Attendance {
  id: number;
  employee: EmployeeMinimal;
  attendance_date: string;
  check_in: string;
  check_out: string | null;
  worked_minutes: number | null;
  overtime_minutes: number | null;
  status: AttendanceStatus;
  notes: string | null;
  corrected_by_name: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface CurrentAttendance {
  checked_in: boolean;
  attendance: Attendance | null;
}

export interface Contract {
  id: number;
  reference: string;
  status: ContractStatus;
  employee: EmployeeMinimal;
  department: Department;
  job_position: JobPosition;
  working_schedule: WorkingScheduleSummary | null;
  department_id: number;
  job_position_id: number;
  working_schedule_id: number | null;
  start_date: string;
  end_date: string | null;
  wage_monthly: string;
  currency: string;
  salary_structure_note: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface TimeOffType {
  id: number;
  name: string;
  code: string | null;
  unit: TimeOffUnit;
  requires_allocation: boolean;
  approval_policy: ApprovalPolicy;
  is_active: boolean;
  display_color: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface TimeOffTypeMinimal {
  id: number;
  name: string;
  unit: TimeOffUnit;
  requires_allocation: boolean;
  is_active: boolean;
}

export interface TimeOffAllocation {
  id: number;
  employee: EmployeeMinimal;
  time_off_type: TimeOffTypeMinimal;
  allocated_amount: string;
  taken_amount: string;
  remaining_amount: string;
  valid_from: string;
  valid_to: string;
  status: AllocationStatus;
  approver_name: string | null;
  approved_at: string | null;
  description: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface AllocationBalanceSnapshot {
  allocation_id: number;
  before: string;
  consumed: string;
  remaining: string;
}

export interface TimeOffRequest {
  id: number;
  employee: EmployeeMinimal;
  time_off_type: TimeOffTypeMinimal;
  start_date: string;
  end_date: string;
  duration_amount: string;
  status: TimeOffRequestStatus;
  reason: string | null;
  approver_name: string | null;
  approved_at: string | null;
  refused_at: string | null;
  allocation_id: number | null;
  balance: AllocationBalanceSnapshot | null;
  created_at: string;
  updated_at: string | null;
}

export interface TimeOffBalance {
  allocation_id: number | null;
  unit: TimeOffUnit;
  allocated: string;
  taken: string;
  remaining: string;
}
