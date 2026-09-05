import { z } from "zod";

export const createDepartmentSchema = z.object({
  name: z.string().min(1),
  code: z.string().min(1),
  description: z.string().optional(),
  isActive: z.boolean().optional(),
});

export const updateDepartmentSchema = createDepartmentSchema.partial();
