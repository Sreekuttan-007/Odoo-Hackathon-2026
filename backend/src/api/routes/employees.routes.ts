import { Router } from "express";
import { requireAuth } from "../../middleware/requireAuth";
import { requireRole, HR_ADMIN_ROLES } from "../../middleware/requireRole";
import {
  createEmployeeSchema,
  updateEmployeeSchema,
  employeeListQuerySchema,
} from "../../schemas/employee.schema";
import * as employeeService from "../../services/employeeService";
import { Errors } from "../../utils/apiError";

export const employeesRouter = Router();

employeesRouter.get("/", requireAuth, requireRole(...HR_ADMIN_ROLES), async (req, res, next) => {
  try {
    const query = employeeListQuerySchema.parse(req.query);
    res.json(await employeeService.listEmployees(query));
  } catch (err) {
    next(err);
  }
});

// EMPLOYEE role may read only their own linked record (0.6); HR_MANAGER+ may
// read any. This is the one Phase 1 endpoint EMPLOYEE can call at all.
employeesRouter.get("/:id", requireAuth, async (req, res, next) => {
  try {
    const isSelf = req.user!.employeeId === req.params.id;
    const isHrAdmin = HR_ADMIN_ROLES.includes(req.user!.role);
    if (!isSelf && !isHrAdmin) {
      throw Errors.forbidden("FORBIDDEN", "You may only view your own employee record");
    }
    res.json(await employeeService.getEmployee(req.params.id));
  } catch (err) {
    next(err);
  }
});

employeesRouter.post("/", requireAuth, requireRole(...HR_ADMIN_ROLES), async (req, res, next) => {
  try {
    const body = createEmployeeSchema.parse(req.body);
    res.status(201).json(await employeeService.createEmployee(body));
  } catch (err) {
    next(err);
  }
});

employeesRouter.patch("/:id", requireAuth, requireRole(...HR_ADMIN_ROLES), async (req, res, next) => {
  try {
    const body = updateEmployeeSchema.parse(req.body);
    res.json(await employeeService.updateEmployee(req.params.id, body));
  } catch (err) {
    next(err);
  }
});
