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
  created_at: string;
  updated_at: string | null;
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
