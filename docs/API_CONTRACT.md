# API Contract

## General Conventions
- All APIs live under `/api/`
- Standard JSON responses
- Error shape:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": null
  }
}
```

## Foundation Endpoints
- `GET /api/health` - Healthcheck
