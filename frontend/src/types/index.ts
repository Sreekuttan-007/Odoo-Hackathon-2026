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
  level: number | null;
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

export type RuleCategory = 'BASIC' | 'ALLOWANCE' | 'GROSS' | 'DEDUCTION' | 'NET';
export type ComputationMethod = 'FIXED' | 'PERCENTAGE' | 'FORMULA';
export type PayrunStatus = 'DRAFT' | 'COMPUTED' | 'VALIDATED' | 'PAID';
export type WarningSeverity = 'BLOCKER' | 'WARNING' | 'INFO';

export interface SalaryStructure {
  id: number;
  name: string;
  code: string | null;
  description: string | null;
  is_active: boolean;
  rule_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface SalaryStructureMinimal {
  id: number;
  name: string;
  is_active: boolean;
}

export interface SalaryRule {
  id: number;
  salary_structure_id: number;
  name: string;
  code: string;
  category: RuleCategory;
  sequence: number;
  computation_method: ComputationMethod;
  fixed_amount: string | null;
  percentage: string | null;
  percentage_base: string | null;
  formula_expression: string | null;
  quantity: string;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface SalaryStructureDetail extends SalaryStructure {
  rules: SalaryRule[];
}

// Payroll Simulator (Phase 9) — deterministic what-if scenarios. Never
// persisted; see backend/app/services/simulator.py for the invariant.
export interface RuleOverrideInput {
  rule_id: number;
  computation_method?: ComputationMethod;
  fixed_amount?: string;
  percentage?: string;
  base_code?: string;
  formula_expression?: string;
  quantity?: string;
}

export interface SimulatedLine {
  rule_code: string;
  rule_name: string;
  category: RuleCategory;
  sequence: number;
  method: ComputationMethod;
  current_amount: string | null;
  simulated_amount: string | null;
  changed: boolean;
}

export interface ScenarioTotals {
  basic: string;
  allowances: string;
  gross: string;
  deductions: string;
  net: string;
}

export interface EmployeeSimulationResult {
  employee_id: number;
  employee_name: string;
  department: string | null;
  excluded: boolean;
  exclusion_code: string | null;
  exclusion_reason: string | null;
  current: ScenarioTotals | null;
  simulated: ScenarioTotals | null;
  delta_gross: string | null;
  delta_deductions: string | null;
  delta_net: string | null;
  delta_net_percent: string | null;
  status: 'INCREASED' | 'DECREASED' | 'UNCHANGED' | 'EXCLUDED';
  components: SimulatedLine[];
}

export interface AggregateImpact {
  current_total_gross: string;
  simulated_total_gross: string;
  delta_gross: string;
  current_total_deductions: string;
  simulated_total_deductions: string;
  delta_deductions: string;
  current_total_net: string;
  simulated_total_net: string;
  delta_net: string;
  employees_increased: number;
  employees_decreased: number;
  employees_unchanged: number;
  is_monthly_period: boolean;
  annualized_net_delta_estimate: string | null;
}

export interface SimulatorRunResponse {
  salary_structure_id: number;
  salary_structure_name: string;
  period_start: string;
  period_end: string;
  employees_selected: number;
  employees_simulated: number;
  employees_excluded: number;
  aggregate: AggregateImpact;
  employees: EmployeeSimulationResult[];
}

export interface EligibleEmployee {
  employee: EmployeeMinimal;
  eligible: boolean;
  reason: string | null;
  working_schedule_summary: string | null;
  wage_monthly: string | null;
}

export interface Payrun {
  id: number;
  reference: string;
  salary_structure: SalaryStructureMinimal;
  period_start: string;
  period_end: string;
  status: PayrunStatus;
  employee_count: number;
  total_gross: string;
  total_net: string;
  warning_count: number;
  created_by_name: string | null;
  computed_at: string | null;
  validated_at: string | null;
  validated_by_name: string | null;
  paid_at: string | null;
  paid_by_name: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface PayslipLine {
  id: number;
  rule_name_snapshot: string;
  rule_code_snapshot: string;
  category_snapshot: RuleCategory;
  sequence_snapshot: number;
  computation_method_snapshot: ComputationMethod;
  base_description_snapshot: string | null;
  amount: string;
  quantity: string | null;
}

export interface PayrollWarning {
  id: number;
  severity: WarningSeverity;
  code: string;
  message: string;
}

export interface Payslip {
  id: number;
  payrun_id: number;
  payrun_reference: string;
  employee: EmployeeMinimal;
  contract_id: number | null;
  salary_structure: SalaryStructureMinimal;
  period_start: string;
  period_end: string;
  status: PayrunStatus;
  worked_days: string | null;
  expected_work_days: string | null;
  worked_hours: string | null;
  basic: string;
  allowances: string;
  gross: string;
  deductions: string;
  net: string;
  warning_count: number;
  lines: PayslipLine[];
  warnings: PayrollWarning[];
  computed_at: string | null;
  validated_at: string | null;
  paid_at: string | null;
  created_at: string;
  updated_at: string | null;
}

// PayTrace (Phase 7) — a deterministic explanation of one Payslip,
// rebuilt entirely from persisted historical snapshots. See
// backend/app/services/paytrace.py.
export interface PayTraceCalculation {
  fixed_amount?: string;
  quantity?: string;
  percentage?: string;
  base_code?: string;
  base_label?: string;
  base_amount?: string;
  formula?: string;
  inputs?: Record<string, string>;
}

export interface PayTraceEntry {
  sequence: number;
  rule_name: string;
  rule_code: string;
  category: 'BASIC' | 'ALLOWANCE' | 'GROSS' | 'DEDUCTION' | 'NET';
  method: 'FIXED' | 'PERCENTAGE' | 'FORMULA';
  quantity: string | null;
  result: string;
  calculation: PayTraceCalculation | null;
  explanation: string;
  depends_on: string[];
  has_structured_history: boolean;
}

export interface PayTraceComponent {
  rule_code: string;
  rule_name: string;
  amount: string;
}

export interface PayTraceAggregates {
  basic: string;
  allowances: string;
  gross: string;
  deductions: string;
  net: string;
  gross_components: PayTraceComponent[];
  net_components: PayTraceComponent[];
}

export interface PayTraceAvailable {
  available: true;
  employee: { id: number; name: string; employee_code: string | null };
  period: { start: string; end: string };
  salary_structure: { id: number; name: string };
  contract: { reference: string; wage_monthly: string; currency: string } | null;
  entries: PayTraceEntry[];
  aggregates: PayTraceAggregates;
}

export interface PayTraceUnavailable {
  available: false;
  reason: 'NOT_COMPUTED' | 'NO_LINES';
  message: string;
}

export type PayTrace = PayTraceAvailable | PayTraceUnavailable;

export interface PayTraceNarration {
  available: boolean;
  reason: string | null;
  summary: string | null;
  components: { rule_code: string; explanation: string }[] | null;
}

// Payroll Preflight (Phase 8) — a deterministic, derived readiness &
// risk assessment of a COMPUTED Payrun. See backend/app/services/preflight.py.
export type PreflightReadiness =
  | 'NOT_RUN'
  | 'ACTION_REQUIRED'
  | 'REVIEW_RECOMMENDED'
  | 'READY';

export interface PreflightFinding {
  code: string;
  severity: WarningSeverity;
  category: string;
  message: string;
  employee_id: number | null;
  employee_name: string | null;
  payslip_id: number | null;
  evidence: Record<string, unknown>;
  resolution: string | null;
}

export interface PreflightResult {
  payrun_id: number;
  reference: string;
  status: PayrunStatus;
  period: { start: string; end: string };
  employee_count: number;
  generated_at: string;
  readiness: PreflightReadiness;
  summary: { blockers: number; warnings: number; info: number };
  findings: PreflightFinding[];
  message: string | null;
}

// Payloom Intelligence (Phase 10) — a grounded AI payroll brief. Every
// figure comes from the deterministic engines; every statement is
// validated against a backend source registry. See
// backend/app/services/intelligence.py.
export interface BriefSource {
  id: string;
  type: 'PAYROLL' | 'PREFLIGHT' | 'SIMULATOR';
  code: string;
  severity: WarningSeverity | null;
  label: string;
  detail: string | null;
  employee_ref: string | null;
  route: string | null;
}

export interface BriefItem {
  title: string;
  text: string;
  priority: WarningSeverity | null;
  source_ids: string[];
  source_type: string | null;
  source_code: string | null;
  source_ref: string | null;
  route: string | null;
}

export interface PayrollBrief {
  available: boolean;
  reason: string | null;
  is_fallback: boolean;
  provider: string | null;
  payrun_id: number;
  reference: string;
  period: { start: string; end: string };
  status: PayrunStatus;
  headline: string | null;
  summary: string | null;
  attention_items: BriefItem[];
  observations: BriefItem[];
  suggested_review_order: BriefItem[];
  sources: BriefSource[];
  deterministic_summary: string;
  generated_at: string;
  evidence_fingerprint: string;
}

export interface PayslipSummary {
  id: number;
  payrun_id: number;
  employee: EmployeeMinimal;
  salary_structure: SalaryStructureMinimal;
  period_start: string;
  period_end: string;
  status: PayrunStatus;
  basic: string;
  gross: string;
  net: string;
  warning_count: number;
}
