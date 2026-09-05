import request from "supertest";
import { app, loginAs, DEMO_USERS } from "./setup";

describe("Departments", () => {
  let token: string;

  beforeAll(async () => {
    token = await loginAs(DEMO_USERS.hrManager);
  });

  it("creates a department", async () => {
    const res = await request(app)
      .post("/api/departments")
      .set("Authorization", `Bearer ${token}`)
      .send({ name: "Quality Assurance", code: "QA" });
    expect(res.status).toBe(201);
    expect(res.body.code).toBe("QA");
  });

  it("rejects a duplicate department code", async () => {
    const res = await request(app)
      .post("/api/departments")
      .set("Authorization", `Bearer ${token}`)
      .send({ name: "Quality Assurance 2", code: "QA" });
    expect(res.status).toBe(409);
    expect(res.body.error.code).toBe("DUPLICATE_DEPARTMENT");
  });

  it("lists departments", async () => {
    const res = await request(app).get("/api/departments").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.data)).toBe(true);
    expect(res.body.data.length).toBeGreaterThan(0);
  });

  it("updates a department", async () => {
    const created = await request(app)
      .post("/api/departments")
      .set("Authorization", `Bearer ${token}`)
      .send({ name: "Legal", code: "LEGAL" });
    const res = await request(app)
      .patch(`/api/departments/${created.body.id}`)
      .set("Authorization", `Bearer ${token}`)
      .send({ description: "Legal & Compliance" });
    expect(res.status).toBe(200);
    expect(res.body.description).toBe("Legal & Compliance");
  });

  it("404s for an unknown department", async () => {
    const res = await request(app)
      .get("/api/departments/00000000-0000-0000-0000-000000000000")
      .set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(404);
    expect(res.body.error.code).toBe("DEPARTMENT_NOT_FOUND");
  });
});
