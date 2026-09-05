from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

from app.api.auth import router as auth_router
from app.api.admin_users import router as admin_users_router
from app.api.people import router as people_router
from app.api.departments import router as departments_router
from app.api.job_positions import router as job_positions_router
from app.api.employees import router as employees_router
from app.api.contracts import router as contracts_router
from app.api.working_schedules import router as working_schedules_router

app = FastAPI(
    title="PeoplePay360 API",
    description="Backend API for PeoplePay360 HR & Payroll system",
    version="0.1.0"
)

# CORS configuration
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Error Handler Format
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
                "details": str(exc) if settings.APP_ENV == "development" else None
            }
        }
    )

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admin_users_router, prefix="/api/admin", tags=["Admin Users"])
app.include_router(departments_router, prefix="/api", tags=["Departments"])
app.include_router(job_positions_router, prefix="/api", tags=["Job Positions"])
app.include_router(employees_router, prefix="/api", tags=["Employees"])
app.include_router(contracts_router, prefix="/api", tags=["Contracts"])
app.include_router(working_schedules_router, prefix="/api", tags=["Working Schedules"])
# Registered last: its GET routes duplicate the routers above (which already
# handle nested working_schedule serialization correctly), so this only
# matters for any path that isn't already covered above.
app.include_router(people_router, prefix="/api", tags=["People"])
