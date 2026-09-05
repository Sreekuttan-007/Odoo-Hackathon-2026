import { Prisma, EmployeeType, EmployeeStatus } from "@prisma/client";
import { prisma } from "../db/client";
import { Errors } from "../utils/apiError";

interface EmployeeInput {
  employeeCode: string;
  firstName: string;
  lastName: string;
  email: string;
  phone?: string | null;
  departmentId: string;
  jobPositionId: string;
  managerId?: string | null;
  employeeType: EmployeeType;
  joinDate: Date;
  status?: EmployeeStatus;
}

interface EmployeeListFilters {
  search?: string;
  departmentId?: string;
  jobPositionId?: string;
  status?: EmployeeStatus;
  employeeType?: EmployeeType;
  page: number;
  pageSize: number;
}

async function assertDepartmentExists(departmentId: string) {
  const department = await prisma.department.findUnique({ where: { id: departmentId } });
  if (!department) {
    throw Errors.badRequest("INVALID_DEPARTMENT", "departmentId does not reference an existing department");
  }
}

async function assertJobPositionExists(jobPositionId: string) {
  const jobPosition = await prisma.jobPosition.findUnique({ where: { id: jobPositionId } });
  if (!jobPosition) {
    throw Errors.badRequest("INVALID_JOB_POSITION", "jobPositionId does not reference an existing job position");
  }
}

// Guards both "manager doesn't exist" and "employee cannot manage themselves"
// (Phase 1 spec §20/§28) — selfId is only known on update, not create.
async function assertManagerValid(managerId: string | null | undefined, selfId?: string) {
  if (!managerId) return;
  if (selfId && managerId === selfId) {
    throw Errors.badRequest("SELF_MANAGER_NOT_ALLOWED", "An employee cannot be their own manager");
  }
  const manager = await prisma.employee.findUnique({ where: { id: managerId } });
  if (!manager) {
    throw Errors.badRequest("INVALID_MANAGER", "managerId does not reference an existing employee");
  }
}

async function assertEmployeeCodeAvailable(employeeCode?: string, excludeId?: string) {
  if (!employeeCode) return;
  const existing = await prisma.employee.findFirst({
    where: { employeeCode, ...(excludeId && { id: { not: excludeId } }) },
  });
  if (existing) {
    throw Errors.conflict("DUPLICATE_EMPLOYEE_CODE", "An employee with this employee code already exists");
  }
}

async function assertEmailAvailable(email?: string, excludeId?: string) {
  if (!email) return;
  const existing = await prisma.employee.findFirst({
    where: { email, ...(excludeId && { id: { not: excludeId } }) },
  });
  if (existing) {
    throw Errors.conflict("DUPLICATE_EMAIL", "An employee with this email already exists");
  }
}

export async function listEmployees(filters: EmployeeListFilters) {
  const where: Prisma.EmployeeWhereInput = {
    ...(filters.departmentId && { departmentId: filters.departmentId }),
    ...(filters.jobPositionId && { jobPositionId: filters.jobPositionId }),
    ...(filters.status && { status: filters.status }),
    ...(filters.employeeType && { employeeType: filters.employeeType }),
    ...(filters.search && {
      OR: [
        { firstName: { contains: filters.search, mode: "insensitive" } },
        { lastName: { contains: filters.search, mode: "insensitive" } },
        { email: { contains: filters.search, mode: "insensitive" } },
        { employeeCode: { contains: filters.search, mode: "insensitive" } },
      ],
    }),
  };

  const [data, total] = await Promise.all([
    prisma.employee.findMany({
      where,
      skip: (filters.page - 1) * filters.pageSize,
      take: filters.pageSize,
      orderBy: { createdAt: "desc" },
      include: { department: true, jobPosition: true },
    }),
    prisma.employee.count({ where }),
  ]);

  // Matches the common list envelope in docs/API_CONTRACT.md §2.
  return { data, total, page: filters.page, pageSize: filters.pageSize };
}

export async function getEmployee(id: string) {
  const employee = await prisma.employee.findUnique({
    where: { id },
    include: { department: true, jobPosition: true, manager: true },
  });
  if (!employee) throw Errors.notFound("EMPLOYEE_NOT_FOUND", "Employee not found");
  return employee;
}

export async function createEmployee(data: EmployeeInput) {
  await assertDepartmentExists(data.departmentId);
  await assertJobPositionExists(data.jobPositionId);
  await assertManagerValid(data.managerId ?? null);
  await assertEmployeeCodeAvailable(data.employeeCode);
  await assertEmailAvailable(data.email);

  return prisma.employee.create({ data });
}

export async function updateEmployee(id: string, data: Partial<EmployeeInput>) {
  await getEmployee(id);

  if (data.departmentId) await assertDepartmentExists(data.departmentId);
  if (data.jobPositionId) await assertJobPositionExists(data.jobPositionId);
  if (data.managerId !== undefined) await assertManagerValid(data.managerId, id);
  await assertEmployeeCodeAvailable(data.employeeCode, id);
  await assertEmailAvailable(data.email, id);

  return prisma.employee.update({ where: { id }, data });
}
