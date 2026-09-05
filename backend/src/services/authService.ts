import { prisma } from "../db/client";
import { verifyPassword } from "../auth/password";
import { signAccessToken } from "../auth/jwt";
import { Errors } from "../utils/apiError";

export async function login(email: string, password: string) {
  const user = await prisma.user.findUnique({ where: { email }, include: { role: true } });
  if (!user) {
    throw Errors.unauthorized("INVALID_CREDENTIALS", "Invalid email or password");
  }
  if (!user.isActive) {
    throw Errors.unauthorized("INACTIVE_USER", "This account is inactive");
  }

  const valid = await verifyPassword(password, user.passwordHash);
  if (!valid) {
    throw Errors.unauthorized("INVALID_CREDENTIALS", "Invalid email or password");
  }

  const token = signAccessToken(user.id);
  return {
    token,
    user: { id: user.id, email: user.email, role: user.role.name, employeeId: user.employeeId },
  };
}

export async function getCurrentUser(userId: string) {
  const user = await prisma.user.findUnique({ where: { id: userId }, include: { role: true } });
  if (!user) throw Errors.notFound("USER_NOT_FOUND", "User not found");
  return { id: user.id, email: user.email, role: user.role.name, employeeId: user.employeeId };
}
