import { prisma } from "../db/client";
import { Errors } from "../utils/apiError";

interface DepartmentInput {
  name: string;
  code: string;
  description?: string;
  isActive?: boolean;
}

export async function listDepartments() {
  return prisma.department.findMany({ orderBy: { name: "asc" } });
}

export async function getDepartment(id: string) {
  const department = await prisma.department.findUnique({ where: { id } });
  if (!department) throw Errors.notFound("DEPARTMENT_NOT_FOUND", "Department not found");
  return department;
}

async function assertNameCodeAvailable(name?: string, code?: string, excludeId?: string) {
  if (!name && !code) return;
  const existing = await prisma.department.findFirst({
    where: {
      ...(excludeId && { id: { not: excludeId } }),
      OR: [...(name ? [{ name }] : []), ...(code ? [{ code }] : [])],
    },
  });
  if (existing) {
    throw Errors.conflict("DUPLICATE_DEPARTMENT", "A department with this name or code already exists");
  }
}

export async function createDepartment(data: DepartmentInput) {
  await assertNameCodeAvailable(data.name, data.code);
  return prisma.department.create({ data });
}

export async function updateDepartment(id: string, data: Partial<DepartmentInput>) {
  await getDepartment(id);
  await assertNameCodeAvailable(data.name, data.code, id);
  return prisma.department.update({ where: { id }, data });
}
