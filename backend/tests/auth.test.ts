import request from "supertest";
import { app, loginAs, DEMO_USERS, DEMO_PASSWORD } from "./setup";
import { prisma } from "../src/db/client";

describe("Authentication", () => {
  it("logs in with valid credentials", async () => {
    const res = await request(app)
      .post("/api/auth/login")
      .send({ email: DEMO_USERS.hrManager, password: DEMO_PASSWORD });
    expect(res.status).toBe(200);
    expect(res.body.token).toBeDefined();
    expect(res.body.user.role).toBe("HR_MANAGER");
  });

  it("rejects an invalid password", async () => {
    const res = await request(app)
      .post("/api/auth/login")
      .send({ email: DEMO_USERS.hrManager, password: "wrong-password" });
    expect(res.status).toBe(401);
    expect(res.body.error.code).toBe("INVALID_CREDENTIALS");
  });

  it("rejects an inactive user", async () => {
    const user = await prisma.user.update({ where: { email: DEMO_USERS.admin }, data: { isActive: false } });
    const res = await request(app)
      .post("/api/auth/login")
      .send({ email: DEMO_USERS.admin, password: DEMO_PASSWORD });
    expect(res.status).toBe(401);
    expect(res.body.error.code).toBe("INACTIVE_USER");
    await prisma.user.update({ where: { id: user.id }, data: { isActive: true } });
  });

  it("requires authentication for /auth/me", async () => {
    const res = await request(app).get("/api/auth/me");
    expect(res.status).toBe(401);
  });

  it("returns the current user for a valid token", async () => {
    const token = await loginAs(DEMO_USERS.hrManager);
    const res = await request(app).get("/api/auth/me").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body.user.email).toBe(DEMO_USERS.hrManager);
  });
});
