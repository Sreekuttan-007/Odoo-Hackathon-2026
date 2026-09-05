import { RoleName } from "@prisma/client";

declare global {
  namespace Express {
    interface Request {
      user?: {
        id: string;
        email: string;
        role: RoleName;
        employeeId: string | null;
      };
    }
  }
}

export {};
