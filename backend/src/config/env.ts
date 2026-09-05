import { z } from "zod";

const envSchema = z.object({
  APP_ENV: z.enum(["development", "test", "production"]).default("development"),
  DATABASE_URL: z.string().min(1, "DATABASE_URL is required"),
  SECRET_KEY: z.string().min(16, "SECRET_KEY must be at least 16 characters"),
  ACCESS_TOKEN_EXPIRE_MINUTES: z.coerce.number().int().positive().default(60),
  CORS_ORIGINS: z.string().default("http://localhost:5173"),
  PORT: z.coerce.number().int().positive().default(4000),
});

function loadEnv() {
  const parsed = envSchema.safeParse(process.env);
  if (!parsed.success) {
    const issues = parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ");
    throw new Error(`Invalid environment configuration: ${issues}`);
  }
  return parsed.data;
}

export const env = loadEnv();
export const corsOrigins = env.CORS_ORIGINS.split(",").map((o) => o.trim());
