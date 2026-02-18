# Personal Journal Monorepo

Монорепозиторий для проекта **Personal Journal**:

- `backend/` — FastAPI (Python 3.11)
- `frontend/` — React + Vite + TypeScript
- `docker-compose.yml` — PostgreSQL

## Требования

- Python 3.11+
- Node.js 20+
- npm 10+
- Docker + Docker Compose

## Структура

```text
.
├── backend/
├── frontend/
└── docker-compose.yml
```

## 1) Запуск базы данных (Postgres)

Из корня репозитория:

```bash
docker compose up -d db
```

Параметры БД по умолчанию:

- host: `localhost`
- port: `5432`
- db: `journal`
- user: `journal`
- password: `journal`

Остановить:

```bash
docker compose down
```

## 2) Запуск backend (FastAPI)

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Backend будет доступен на `http://localhost:8000`.
Проверка health endpoint: `GET http://localhost:8000/health`.

### Переменные окружения backend

В `backend/.env`:

```env
DATABASE_URL=postgresql://journal:journal@localhost:5432/journal
```

## 3) Запуск frontend (React + Vite + TypeScript)

```bash
cd frontend
npm install
npm run dev -- --host --port 5173
```

Frontend будет доступен на `http://localhost:5173`.

## Быстрый старт (3 терминала)

1. `docker compose up -d db`
2. Backend: `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000`
3. Frontend: `cd frontend && npm run dev -- --host --port 5173`
