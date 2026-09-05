import request from "supertest";
import { createApp } from "../src/app";

export const app = createApp();
export const DEMO_PASSWORD = "Password123!";

export const DEMO_USERS = {
  employee: "employee@example.com",
  hrManager: "hr@example.com",
  payrollUser: "payroll@example.com",
  payrollManager: "payrollmanager@example.com",
  admin: "admin@example.com",
};

export async function loginAs(email: string): Promise<string> {
  const res = await request(app).post("/api/auth/login").send({ email, password: DEMO_PASSWORD });
  if (res.status !== 200) {
    throw new Error(`Login failed for ${email}: ${JSON.stringify(res.body)}`);
  }
  return res.body.token as string;
}
