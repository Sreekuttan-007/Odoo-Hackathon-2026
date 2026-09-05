import { execSync } from "child_process";
import path from "path";

// Resets the test database schema and re-applies the deterministic seed
// before every test run, so tests never depend on leftover state from a
// prior run (Phase 1 spec §35/§36).
export default async function globalSetup() {
  const cwd = path.resolve(__dirname, "..");
  execSync("npx prisma migrate reset --force --skip-generate", {
    cwd,
    env: process.env,
    stdio: "inherit",
  });
}
