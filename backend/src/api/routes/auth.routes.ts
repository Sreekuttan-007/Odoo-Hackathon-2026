import { Router } from "express";
import { loginSchema } from "../../schemas/auth.schema";
import { login, getCurrentUser } from "../../services/authService";
import { requireAuth } from "../../middleware/requireAuth";

export const authRouter = Router();

authRouter.post("/login", async (req, res, next) => {
  try {
    const body = loginSchema.parse(req.body);
    const result = await login(body.email, body.password);
    res.json(result);
  } catch (err) {
    next(err);
  }
});

authRouter.get("/me", requireAuth, async (req, res, next) => {
  try {
    const user = await getCurrentUser(req.user!.id);
    res.json({ user });
  } catch (err) {
    next(err);
  }
});
