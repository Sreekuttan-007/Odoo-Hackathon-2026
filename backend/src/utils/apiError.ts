export class ApiError extends Error {
  status: number;
  code: string;
  details: unknown;

  constructor(status: number, code: string, message: string, details: unknown = null) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export const Errors = {
  notFound: (code: string, message: string) => new ApiError(404, code, message),
  conflict: (code: string, message: string, details: unknown = null) => new ApiError(409, code, message, details),
  badRequest: (code: string, message: string, details: unknown = null) => new ApiError(400, code, message, details),
  unauthorized: (code: string, message: string) => new ApiError(401, code, message),
  forbidden: (code: string, message: string) => new ApiError(403, code, message),
};
