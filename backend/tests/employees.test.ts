import request from "supertest";
import { app, loginAs, DEMO_USERS } from "./setup";
import { prisma } from "../src/db/client";

describe("Employees", () => {
  let token: string;
  let departmentId: string;
  let jobPositionId: string;

  beforeAll(async () => {
    token = await loginAs(DEMO_USERS.hrManager);
    const dept = await prisma.department.findUnique({ where: { code: "ENG" } });
    departmentId = dept!.id;
    const jp = await prisma.jobPosition.findUnique({ where: { code: "ENG-SWE" } });
    jobPositionId = jp!.id;
  });

  const basePayload = () => ({
    firstName: "Test",
    lastName: "Employee",
    departmentId,
    jobPositionId,
    employeeType: "FULL_TIME",
    joinDate: "2026-01-01",
  });

  it("creates an employee", async () => {
    const res = await request(app)
      .post("/api/employees")
      .set("Authorization", `Bearer ${token}`)
      .send({ ...basePayload(), employeeCode: "EMP-9100", email: "test.employee9100@peoplepay360.dev" });
    expect(res.status).toBe(201);
    expect(res.body.employeeCode).toBe("EMP-9100");
  });

  it("rejects a duplicate employee code", async () => {
    const res = await request(app)
      .post("/api/employees")
      .set("Authorization", `Bearer ${token}`)
      .send({ ...basePayload(), employeeCode: "EMP-9100", email: "different9100@peoplepay360.dev" });
    expect(res.status).toBe(409);
    expect(res.body.error.code).toBe("DUPLICATE_EMPLOYEE_CODE");
  });

  it("rejects a duplicate email", async () => {
    const res = await request(app)
      .post("/api/employees")
      .set("Authorization", `Bearer ${token}`)
      .send({ ...basePayload(), employeeCode: "EMP-9101", email: "test.employee9100@peoplepay360.dev" });
    expect(res.status).toBe(409);
    expect(res.body.error.code).toBe("DUPLICATE_EMAIL");
  });

  it("gets an employee by id", async () => {
    const created = await request(app)
      .post("/api/employees")
      .set("Authorization", `Bearer ${token}`)
      .send({ ...basePayload(), employeeCode: "EMP-9102", email: "emp9102@peoplepay360.dev" });
    const res = await request(app)
      .get(`/api/employees/${created.body.id}`)
      .set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body.id).toBe(created.body.id);
  });

  it("updates an employee", async () => {
    const created = await request(app)
      .post("/api/employees")
      .set("Authorization", `Bearer ${token}`)
      .send({ ...basePayload(), employeeCode: "EMP-9103", email: "emp9103@peoplepay360.dev" });
    const res = await request(app)
      .patch(`/api/employees/${created.body.id}`)
      .set("Authorization", `Bearer ${token}`)
      .send({ phone: "+91-9999999999" });
    expect(res.status).toBe(200);
    expect(res.body.phone).toBe("+91-9999999999");
  });

  it("rejects an invalid department reference", async () => {
    const res = await request(app)
      .post("/api/employees")
      .set("Authorization", `Bearer ${token}`)
      .send({
        ...basePayload(),
        employeeCode: "EMP-9104",
        email: "emp9104@peoplepay360.dev",
        departmentId: "00000000-0000-0000-0000-000000000000",
      });
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe("INVALID_DEPARTMENT");
  });

  it("rejects an invalid manager reference", async () => {
    const res = await request(app)
      .post("/api/employees")
      .set("Authorization", `Bearer ${token}`)
      .send({
        ...basePayload(),
        employeeCode: "EMP-9105",
        email: "emp9105@peoplepay360.dev",
        managerId: "00000000-0000-0000-0000-000000000000",
      });
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe("INVALID_MANAGER");
  });

  it("rejects an employee being set as their own manager", async () => {
    const created = await request(app)
      .post("/api/employees")
      .set("Authorization", `Bearer ${token}`)
      .send({ ...basePayload(), employeeCode: "EMP-9106", email: "emp9106@peoplepay360.dev" });
    const res = await request(app)
      .patch(`/api/employees/${created.body.id}`)
      .set("Authorization", `Bearer ${token}`)
      .send({ managerId: created.body.id });
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe("SELF_MANAGER_NOT_ALLOWED");
  });

  it("supports list filters", async () => {
    const res = await request(app)
      .get(`/api/employees?departmentId=${departmentId}&employeeType=FULL_TIME`)
      .set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body.data.every((e: { departmentId: string }) => e.departmentId === departmentId)).toBe(true);
  });

  it("lets an employee view their own record but forbids viewing another's", async () => {
    const empToken = await loginAs(DEMO_USERS.employee);
    const meRes = await request(app).get("/api/auth/me").set("Authorization", `Bearer ${empToken}`);
    const selfId = meRes.body.user.employeeId as string;

    const selfRes = await request(app).get(`/api/employees/${selfId}`).set("Authorization", `Bearer ${empToken}`);
    expect(selfRes.status).toBe(200);

    const created = await request(app)
      .post("/api/employees")
      .set("Authorization", `Bearer ${token}`)
      .send({ ...basePayload(), employeeCode: "EMP-9107", email: "emp9107@peoplepay360.dev" });

    const otherRes = await request(app)
      .get(`/api/employees/${created.body.id}`)
      .set("Authorization", `Bearer ${empToken}`);
    expect(otherRes.status).toBe(403);
  });
});
