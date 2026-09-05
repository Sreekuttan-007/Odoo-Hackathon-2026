import { z } from "zod";

export const createJobPositionSchema = z.object({
  title: z.string().min(1),
  code: z.string().min(1),
  departmentId: z.string().uuid(),
  description: z.string().optional(),
  isActive: z.boolean().optional(),
});

export const updateJobPositionSchema = createJobPositionSchema.partial();

export const jobPositionListQuerySchema = z.object({
  departmentId: z.string().uuid().optional(),
});
