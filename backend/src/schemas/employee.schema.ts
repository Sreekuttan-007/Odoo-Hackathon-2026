import { z } from "zod";

export const employeeTypeEnum = z.enum(["FULL_TIME", "PART_TIME", "CONTRACTOR"]);
export const employeeStatusEnum = z.enum(["ACTIVE", "INACTIVE", "TERMINATED"]);

export const createEmployeeSchema = z.object({
  employeeCode: z.string().min(1),
  firstName: z.string().min(1),
  lastName: z.string().min(1),
  email: z.string().email(),
  phone: z.string().optional(),
  departmentId: z.string().uuid(),
  jobPositionId: z.string().uuid(),
  managerId: z.string().uuid().optional().nullable(),
  employeeType: employeeTypeEnum,
  joinDate: z.coerce.date(),
  status: employeeStatusEnum.optional(),
});

export const updateEmployeeSchema = createEmployeeSchema.partial();

export const employeeListQuerySchema = z.object({
  search: z.string().optional(),
  departmentId: z.string().uuid().optional(),
  jobPositionId: z.string().uuid().optional(),
  status: employeeStatusEnum.optional(),
  employeeType: employeeTypeEnum.optional(),
  page: z.coerce.number().int().positive().default(1),
  pageSize: z.coerce.number().int().positive().max(100).default(25),
});
