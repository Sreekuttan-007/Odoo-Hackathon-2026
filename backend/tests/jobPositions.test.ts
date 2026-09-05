import request from "supertest";
import { app, loginAs, DEMO_USERS } from "./setup";
import { prisma } from "../src/db/client";

describe("Job Positions", () => {
  let token: string;
  let departmentId: string;

  beforeAll(async () => {
    token = await loginAs(DEMO_USERS.hrManager);
    const dept = await prisma.department.findUnique({ where: { code: "ENG" } });
    departmentId = dept!.id;
  });

  it("creates a job position under a valid department", async () => {
    const res = await request(app)
      .post("/api/job-positions")
      .set("Authorization", `Bearer ${token}`)
      .send({ title: "QA Engineer", code: "ENG-QA", departmentId });
    expect(res.status).toBe(201);
    expect(res.body.departmentId).toBe(departmentId);
  });

  it("rejects a job position with an invalid department", async () => {
    const res = await request(app)
      .post("/api/job-positions")
      .set("Authorization", `Bearer ${token}`)
      .send({ title: "Ghost Role", code: "GHOST-1", departmentId: "00000000-0000-0000-0000-000000000000" });
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe("INVALID_DEPARTMENT");
  });

  it("rejects a duplicate job position code", async () => {
    const res = await request(app)
      .post("/api/job-positions")
      .set("Authorization", `Bearer ${token}`)
      .send({ title: "QA Engineer Duplicate", code: "ENG-QA", departmentId });
    expect(res.status).toBe(409);
    expect(res.body.error.code).toBe("DUPLICATE_JOB_POSITION_CODE");
  });

  it("filters job positions by department", async () => {
    const res = await request(app)
      .get(`/api/job-positions?departmentId=${departmentId}`)
      .set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body.data.every((jp: { departmentId: string }) => jp.departmentId === departmentId)).toBe(true);
  });
});
