import request from "supertest";
import { app, loginAs, DEMO_USERS } from "./setup";

describe("RBAC", () => {
  it("prevents an unauthenticated request from listing employees", async () => {
    const res = await request(app).get("/api/employees");
    expect(res.status).toBe(401);
  });

  it("prevents an Employee from creating an Employee", async () => {
    const token = await loginAs(DEMO_USERS.employee);
    const res = await request(app)
      .post("/api/employees")
      .set("Authorization", `Bearer ${token}`)
      .send({
        employeeCode: "EMP-9001",
        firstName: "X",
        lastName: "Y",
        email: "x.y@peoplepay360.dev",
        departmentId: "00000000-0000-0000-0000-000000000000",
        jobPositionId: "00000000-0000-0000-0000-000000000000",
        employeeType: "FULL_TIME",
        joinDate: "2026-01-01",
      });
    expect(res.status).toBe(403);
    expect(res.body.error.code).toBe("FORBIDDEN");
  });

  it("prevents an Employee from listing employees", async () => {
    const token = await loginAs(DEMO_USERS.employee);
    const res = await request(app).get("/api/employees").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(403);
  });

  it("allows an HR Manager to list employees", async () => {
    const token = await loginAs(DEMO_USERS.hrManager);
    const res = await request(app).get("/api/employees").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
  });

  it("allows Admin to access privileged employee endpoints", async () => {
    const token = await loginAs(DEMO_USERS.admin);
    const res = await request(app).get("/api/employees").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
  });
});
