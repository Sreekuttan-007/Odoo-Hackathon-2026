import { Router } from "express";
import { healthRouter } from "./health.routes";
import { authRouter } from "./auth.routes";
import { employeesRouter } from "./employees.routes";
import { departmentsRouter } from "./departments.routes";
import { jobPositionsRouter } from "./jobPositions.routes";

export const apiRouter = Router();

apiRouter.use("/health", healthRouter);
apiRouter.use("/auth", authRouter);
apiRouter.use("/employees", employeesRouter);
apiRouter.use("/departments", departmentsRouter);
apiRouter.use("/job-positions", jobPositionsRouter);
