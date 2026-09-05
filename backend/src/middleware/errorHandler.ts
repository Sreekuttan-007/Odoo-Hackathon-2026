import { ErrorRequestHandler } from "express";
import { ZodError } from "zod";
import { ApiError } from "../utils/apiError";

// Consistent error envelope for every failure mode, per Phase 1 spec §29:
// { "error": { "code": "...", "message": "...", "details": null } }
export const errorHandler: ErrorRequestHandler = (err, _req, res, _next) => {
  if (err instanceof ApiError) {
    res.status(err.status).json({
      error: { code: err.code, message: err.message, details: err.details ?? null },
    });
    return;
  }

  if (err instanceof ZodError) {
    res.status(400).json({
      error: {
        code: "VALIDATION_ERROR",
        message: "Request validation failed",
        details: err.issues.map((i) => ({ path: i.path.join("."), message: i.message })),
      },
    });
    return;
  }

  // Never log secrets/tokens/passwords — see Phase 1 spec §38.
  // eslint-disable-next-line no-console
  console.error(err);
  res.status(500).json({
    error: { code: "INTERNAL_ERROR", message: "An unexpected error occurred", details: null },
  });
};
