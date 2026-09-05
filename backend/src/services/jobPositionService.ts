import { prisma } from "../db/client";
import { Errors } from "../utils/apiError";

interface JobPositionInput {
  title: string;
  code: string;
  departmentId: string;
  description?: string;
  isActive?: boolean;
}

async function assertDepartmentExists(departmentId: string) {
  const department = await prisma.department.findUnique({ where: { id: departmentId } });
  if (!department) {
    throw Errors.badRequest("INVALID_DEPARTMENT", "departmentId does not reference an existing department");
  }
}

async function assertCodeAvailable(code?: string, excludeId?: string) {
  if (!code) return;
  const existing = await prisma.jobPosition.findFirst({
    where: { code, ...(excludeId && { id: { not: excludeId } }) },
  });
  if (existing) {
    throw Errors.conflict("DUPLICATE_JOB_POSITION_CODE", "A job position with this code already exists");
  }
}

export async function listJobPositions(departmentId?: string) {
  return prisma.jobPosition.findMany({
    where: departmentId ? { departmentId } : undefined,
    orderBy: { title: "asc" },
  });
}

export async function getJobPosition(id: string) {
  const jobPosition = await prisma.jobPosition.findUnique({ where: { id } });
  if (!jobPosition) throw Errors.notFound("JOB_POSITION_NOT_FOUND", "Job position not found");
  return jobPosition;
}

export async function createJobPosition(data: JobPositionInput) {
  await assertDepartmentExists(data.departmentId);
  await assertCodeAvailable(data.code);
  return prisma.jobPosition.create({ data });
}

export async function updateJobPosition(id: string, data: Partial<JobPositionInput>) {
  await getJobPosition(id);
  if (data.departmentId) await assertDepartmentExists(data.departmentId);
  await assertCodeAvailable(data.code, id);
  return prisma.jobPosition.update({ where: { id }, data });
}
