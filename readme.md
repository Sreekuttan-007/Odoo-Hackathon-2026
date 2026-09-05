# PeoplePay360

PeoplePay360 is an enterprise HR & Payroll application.

## Repository Structure

- `/frontend` - React + Vite + TypeScript SPA
- `/backend` - FastAPI + Python API
- `/docs` - Project documentation and Phase tracking

## Local Development

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Backend
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Current Status
See `docs/BUILD_STATUS.md` and `docs/PHASE_LOG.md` for current hackathon progress.
