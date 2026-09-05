import { RequestHandler } from "express";
import { verifyAccessToken } from "../auth/jwt";
import { prisma } from "../db/client";
import { Errors } from "../utils/apiError";

export const requireAuth: RequestHandler = async (req, _res, next) => {
  try {
    const header = req.headers.authorization;
    if (!header?.startsWith("Bearer ")) {
      throw Errors.unauthorized("UNAUTHORIZED", "Missing or malformed Authorization header");
    }
    const token = header.slice("Bearer ".length);

    let payload;
    try {
      payload = verifyAccessToken(token);
    } catch (err) {
      if (err instanceof Error && err.name === "TokenExpiredError") {
        throw Errors.unauthorized("TOKEN_EXPIRED", "Token has expired");
      }
      throw Errors.unauthorized("INVALID_TOKEN", "Invalid token");
    }

    // Looked up fresh on every request (not trusted from stale JWT claims)
    // so a role change or deactivation takes effect immediately.
    const user = await prisma.user.findUnique({
      where: { id: payload.sub },
      include: { role: true },
    });

    if (!user || !user.isActive) {
      throw Errors.unauthorized("INACTIVE_USER", "User is inactive or does not exist");
    }

    req.user = {
      id: user.id,
      email: user.email,
      role: user.role.name,
      employeeId: user.employeeId,
    };
    next();
  } catch (err) {
    next(err);
  }
};
