# journal

## Backend data model

Проект содержит базовые SQLAlchemy-модели и Alembic-миграцию для PostgreSQL:

- `journals` — папки пользователя.
- `articles` — страницы внутри журнала (со `slug`, уникальным в рамках журнала).
- `article_links` — ссылки между страницами.
- `article_sequence` — упорядоченные связи между страницами внутри журнала.

`content_json` хранит структурированный JSON (например, Editor.js),
а `content_text` — плоский текст для быстрого полнотекстового/LIKE-поиска без отдельного движка.

## Миграции Alembic

1. Установи зависимости (минимум: `sqlalchemy`, `alembic`, `psycopg`, `pydantic`).
2. Проверь строку подключения в `alembic.ini` (`sqlalchemy.url`).
3. Примени миграции:

```bash
alembic upgrade head
```

Откат последней миграции:

```bash
alembic downgrade -1
```
