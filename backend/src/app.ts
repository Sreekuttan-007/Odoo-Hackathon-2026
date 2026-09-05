import express from "express";
import cors from "cors";
import { apiRouter } from "./api/routes";
import { errorHandler } from "./middleware/errorHandler";
import { corsOrigins } from "./config/env";
import { Errors } from "./utils/apiError";

export function createApp() {
  const app = express();
  app.use(cors({ origin: corsOrigins }));
  app.use(express.json());
  app.use("/api", apiRouter);
  app.use((req, _res, next) => next(Errors.notFound("NOT_FOUND", `No route for ${req.method} ${req.path}`)));
  app.use(errorHandler);
  return app;
}
