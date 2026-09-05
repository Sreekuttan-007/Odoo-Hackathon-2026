import { PrismaClient, RoleName, EmployeeType, EmployeeStatus, BankDetailsStatus } from "@prisma/client";
import bcrypt from "bcrypt";

const prisma = new PrismaClient();

// Fixed, reproducible password for every demo user (Phase 1 spec §33).
// Development-only — never used outside local/demo environments.
const DEMO_PASSWORD = "Password123!";

async function upsertRole(name: RoleName) {
  return prisma.role.upsert({ where: { name }, update: {}, create: { name } });
}

async function main() {
  const roleNames: RoleName[] = ["EMPLOYEE", "HR_MANAGER", "HR_PAYROLL_USER", "HR_PAYROLL_MANAGER", "ADMIN"];
  const roles = await Promise.all(roleNames.map(upsertRole));
  const roleByName = Object.fromEntries(roles.map((r) => [r.name, r])) as Record<RoleName, (typeof roles)[number]>;

  const departmentSeeds = [
    { name: "Engineering", code: "ENG" },
    { name: "Human Resources", code: "HR" },
    { name: "Finance", code: "FIN" },
    { name: "Sales", code: "SALES" },
    { name: "Operations", code: "OPS" },
  ];
  const departments = await Promise.all(
    departmentSeeds.map((d) => prisma.department.upsert({ where: { code: d.code }, update: {}, create: d }))
  );
  const deptByCode = Object.fromEntries(departments.map((d) => [d.code, d]));

  const jobPositionSeeds = [
    { title: "Software Engineer", code: "ENG-SWE", departmentCode: "ENG" },
    { title: "Senior Software Engineer", code: "ENG-SR-SWE", departmentCode: "ENG" },
    { title: "HR Manager", code: "HR-MGR", departmentCode: "HR" },
    { title: "Payroll Specialist", code: "HR-PAYROLL", departmentCode: "HR" },
    { title: "Finance Analyst", code: "FIN-ANALYST", departmentCode: "FIN" },
    { title: "Sales Executive", code: "SALES-EXEC", departmentCode: "SALES" },
    { title: "Operations Manager", code: "OPS-MGR", departmentCode: "OPS" },
  ];
  const jobPositions = await Promise.all(
    jobPositionSeeds.map((jp) =>
      prisma.jobPosition.upsert({
        where: { code: jp.code },
        update: {},
        create: { title: jp.title, code: jp.code, departmentId: deptByCode[jp.departmentCode].id },
      })
    )
  );
  const jpByCode = Object.fromEntries(jobPositions.map((j) => [j.code, j]));

  const passwordHash = await bcrypt.hash(DEMO_PASSWORD, 12);

  // Manager first — no manager of her own (mirrors DEMO_FLOW.md seed data).
  const priya = await prisma.employee.upsert({
    where: { employeeCode: "EMP-1000" },
    update: {},
    create: {
      employeeCode: "EMP-1000",
      firstName: "Priya",
      lastName: "Sharma",
      email: "priya.sharma@peoplepay360.dev",
      departmentId: deptByCode["ENG"].id,
      jobPositionId: jpByCode["ENG-SR-SWE"].id,
      employeeType: EmployeeType.FULL_TIME,
      joinDate: new Date("2022-03-01"),
      bankDetailsStatus: BankDetailsStatus.PROVIDED,
      status: EmployeeStatus.ACTIVE,
    },
  });

  const arjun = await prisma.employee.upsert({
    where: { employeeCode: "EMP-1001" },
    update: {},
    create: {
      employeeCode: "EMP-1001",
      firstName: "Arjun",
      lastName: "Mehta",
      email: "arjun.mehta@peoplepay360.dev",
      departmentId: deptByCode["ENG"].id,
      jobPositionId: jpByCode["ENG-SWE"].id,
      managerId: priya.id,
      employeeType: EmployeeType.FULL_TIME,
      joinDate: new Date("2024-06-15"),
      bankDetailsStatus: BankDetailsStatus.PROVIDED,
      status: EmployeeStatus.ACTIVE,
    },
  });

  const hrManagerEmployee = await prisma.employee.upsert({
    where: { employeeCode: "EMP-1002" },
    update: {},
    create: {
      employeeCode: "EMP-1002",
      firstName: "Neha",
      lastName: "Kapoor",
      email: "neha.kapoor@peoplepay360.dev",
      departmentId: deptByCode["HR"].id,
      jobPositionId: jpByCode["HR-MGR"].id,
      employeeType: EmployeeType.FULL_TIME,
      joinDate: new Date("2021-01-10"),
      bankDetailsStatus: BankDetailsStatus.PROVIDED,
      status: EmployeeStatus.ACTIVE,
    },
  });

  // Deliberately seeded with MISSING bank details so the Phase 6+ payroll
  // validation matrix has a real, non-fake warning case to demo against
  // (RISKS.md, DEMO_FLOW.md).
  const payrollSpecialist = await prisma.employee.upsert({
    where: { employeeCode: "EMP-1003" },
    update: {},
    create: {
      employeeCode: "EMP-1003",
      firstName: "Rahul",
      lastName: "Verma",
      email: "rahul.verma@peoplepay360.dev",
      departmentId: deptByCode["HR"].id,
      jobPositionId: jpByCode["HR-PAYROLL"].id,
      managerId: hrManagerEmployee.id,
      employeeType: EmployeeType.FULL_TIME,
      joinDate: new Date("2023-02-20"),
      bankDetailsStatus: BankDetailsStatus.MISSING,
      status: EmployeeStatus.ACTIVE,
    },
  });

  const financeAnalyst = await prisma.employee.upsert({
    where: { employeeCode: "EMP-1004" },
    update: {},
    create: {
      employeeCode: "EMP-1004",
      firstName: "Sana",
      lastName: "Iyer",
      email: "sana.iyer@peoplepay360.dev",
      departmentId: deptByCode["FIN"].id,
      jobPositionId: jpByCode["FIN-ANALYST"].id,
      employeeType: EmployeeType.FULL_TIME,
      joinDate: new Date("2023-08-05"),
      bankDetailsStatus: BankDetailsStatus.PROVIDED,
      status: EmployeeStatus.ACTIVE,
    },
  });

  await prisma.employee.upsert({
    where: { employeeCode: "EMP-1005" },
    update: {},
    create: {
      employeeCode: "EMP-1005",
      firstName: "Karan",
      lastName: "Malhotra",
      email: "karan.malhotra@peoplepay360.dev",
      departmentId: deptByCode["SALES"].id,
      jobPositionId: jpByCode["SALES-EXEC"].id,
      employeeType: EmployeeType.CONTRACTOR,
      joinDate: new Date("2025-01-15"),
      bankDetailsStatus: BankDetailsStatus.PROVIDED,
      status: EmployeeStatus.ACTIVE,
    },
  });

  const adminEmployee = await prisma.employee.upsert({
    where: { employeeCode: "EMP-1006" },
    update: {},
    create: {
      employeeCode: "EMP-1006",
      firstName: "System",
      lastName: "Admin",
      email: "system.admin@peoplepay360.dev",
      departmentId: deptByCode["OPS"].id,
      jobPositionId: jpByCode["OPS-MGR"].id,
      employeeType: EmployeeType.FULL_TIME,
      joinDate: new Date("2020-01-01"),
      bankDetailsStatus: BankDetailsStatus.PROVIDED,
      status: EmployeeStatus.ACTIVE,
    },
  });

  const extras = [
    { code: "EMP-1007", first: "Divya", last: "Nair", dept: "OPS", jp: "OPS-MGR" },
    { code: "EMP-1008", first: "Rohan", last: "Gupta", dept: "SALES", jp: "SALES-EXEC" },
  ];
  for (const e of extras) {
    await prisma.employee.upsert({
      where: { employeeCode: e.code },
      update: {},
      create: {
        employeeCode: e.code,
        firstName: e.first,
        lastName: e.last,
        email: `${e.first.toLowerCase()}.${e.last.toLowerCase()}@peoplepay360.dev`,
        departmentId: deptByCode[e.dept].id,
        jobPositionId: jpByCode[e.jp].id,
        employeeType: EmployeeType.FULL_TIME,
        joinDate: new Date("2024-01-01"),
        bankDetailsStatus: BankDetailsStatus.PROVIDED,
        status: EmployeeStatus.ACTIVE,
      },
    });
  }

  // One demo login per canonical role (Phase 1 spec §33).
  const demoUsers: { email: string; roleName: RoleName; employeeId: string | null }[] = [
    { email: "employee@example.com", roleName: "EMPLOYEE", employeeId: arjun.id },
    { email: "hr@example.com", roleName: "HR_MANAGER", employeeId: hrManagerEmployee.id },
    { email: "payroll@example.com", roleName: "HR_PAYROLL_USER", employeeId: payrollSpecialist.id },
    { email: "payrollmanager@example.com", roleName: "HR_PAYROLL_MANAGER", employeeId: financeAnalyst.id },
    { email: "admin@example.com", roleName: "ADMIN", employeeId: adminEmployee.id },
  ];

  for (const u of demoUsers) {
    await prisma.user.upsert({
      where: { email: u.email },
      update: {},
      create: {
        email: u.email,
        passwordHash,
        roleId: roleByName[u.roleName].id,
        employeeId: u.employeeId,
        isActive: true,
      },
    });
  }

  // eslint-disable-next-line no-console
  console.log(`Seed complete. Demo password for all demo users: ${DEMO_PASSWORD}`);
}

main()
  .catch((e) => {
    // eslint-disable-next-line no-console
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
