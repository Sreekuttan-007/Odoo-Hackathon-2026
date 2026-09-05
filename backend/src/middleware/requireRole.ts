import { RequestHandler } from "express";
import { RoleName } from "@prisma/client";
import { Errors } from "../utils/apiError";

export const requireRole = (...roles: RoleName[]): RequestHandler => {
  return (req, _res, next) => {
    if (!req.user) {
      return next(Errors.unauthorized("UNAUTHORIZED", "Authentication required"));
    }
    if (!roles.includes(req.user.role)) {
      return next(Errors.forbidden("FORBIDDEN", "You do not have permission to perform this action"));
    }
    next();
  };
};

// Per REQUIREMENTS.md permission matrix (0.6): HR_PAYROLL_USER and
// HR_PAYROLL_MANAGER inherit all HR_MANAGER HR-administration abilities.
// ADMIN has full access. Phase 1's HR-admin surface (Employees, Departments,
// Job Positions) is gated behind this set.
export const HR_ADMIN_ROLES: RoleName[] = [
  RoleName.HR_MANAGER,
  RoleName.HR_PAYROLL_USER,
  RoleName.HR_PAYROLL_MANAGER,
  RoleName.ADMIN,
];
