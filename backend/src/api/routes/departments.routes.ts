import { Router } from "express";
import { requireAuth } from "../../middleware/requireAuth";
import { requireRole, HR_ADMIN_ROLES } from "../../middleware/requireRole";
import { createDepartmentSchema, updateDepartmentSchema } from "../../schemas/department.schema";
import * as departmentService from "../../services/departmentService";

export const departmentsRouter = Router();

departmentsRouter.get("/", requireAuth, requireRole(...HR_ADMIN_ROLES), async (_req, res, next) => {
  try {
    res.json({ data: await departmentService.listDepartments() });
  } catch (err) {
    next(err);
  }
});

departmentsRouter.get("/:id", requireAuth, requireRole(...HR_ADMIN_ROLES), async (req, res, next) => {
  try {
    res.json(await departmentService.getDepartment(req.params.id));
  } catch (err) {
    next(err);
  }
});

departmentsRouter.post("/", requireAuth, requireRole(...HR_ADMIN_ROLES), async (req, res, next) => {
  try {
    const body = createDepartmentSchema.parse(req.body);
    res.status(201).json(await departmentService.createDepartment(body));
  } catch (err) {
    next(err);
  }
});

departmentsRouter.patch("/:id", requireAuth, requireRole(...HR_ADMIN_ROLES), async (req, res, next) => {
  try {
    const body = updateDepartmentSchema.parse(req.body);
    res.json(await departmentService.updateDepartment(req.params.id, body));
  } catch (err) {
    next(err);
  }
});
