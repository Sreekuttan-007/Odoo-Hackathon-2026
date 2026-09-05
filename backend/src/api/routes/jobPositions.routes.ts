import { Router } from "express";
import { requireAuth } from "../../middleware/requireAuth";
import { requireRole, HR_ADMIN_ROLES } from "../../middleware/requireRole";
import {
  createJobPositionSchema,
  updateJobPositionSchema,
  jobPositionListQuerySchema,
} from "../../schemas/jobPosition.schema";
import * as jobPositionService from "../../services/jobPositionService";

export const jobPositionsRouter = Router();

jobPositionsRouter.get("/", requireAuth, requireRole(...HR_ADMIN_ROLES), async (req, res, next) => {
  try {
    const { departmentId } = jobPositionListQuerySchema.parse(req.query);
    res.json({ data: await jobPositionService.listJobPositions(departmentId) });
  } catch (err) {
    next(err);
  }
});

jobPositionsRouter.get("/:id", requireAuth, requireRole(...HR_ADMIN_ROLES), async (req, res, next) => {
  try {
    res.json(await jobPositionService.getJobPosition(req.params.id));
  } catch (err) {
    next(err);
  }
});

jobPositionsRouter.post("/", requireAuth, requireRole(...HR_ADMIN_ROLES), async (req, res, next) => {
  try {
    const body = createJobPositionSchema.parse(req.body);
    res.status(201).json(await jobPositionService.createJobPosition(body));
  } catch (err) {
    next(err);
  }
});

jobPositionsRouter.patch("/:id", requireAuth, requireRole(...HR_ADMIN_ROLES), async (req, res, next) => {
  try {
    const body = updateJobPositionSchema.parse(req.body);
    res.json(await jobPositionService.updateJobPosition(req.params.id, body));
  } catch (err) {
    next(err);
  }
});
