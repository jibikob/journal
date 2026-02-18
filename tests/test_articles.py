from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.utils import extract_editorjs_text

SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_create_article_generates_slug_and_text():
    journal_resp = client.post("/api/journals", json={"title": "Tech Journal"})
    assert journal_resp.status_code == 201
    journal_id = journal_resp.json()["id"]

    payload = {
        "title": "Hello FastAPI",
        "content_json": {
            "blocks": [
                {"type": "paragraph", "data": {"text": "<b>Intro</b> text"}},
                {"type": "list", "data": {"items": ["one", "two"]}},
            ]
        },
    }

    article_resp = client.post(f"/api/journals/{journal_id}/articles", json=payload)
    assert article_resp.status_code == 201

    data = article_resp.json()
    assert data["slug"] == "hello-fastapi"
    assert data["content_text"] == "Intro text\none\ntwo"


def test_extract_editorjs_text():
    content = {
        "blocks": [
            {"type": "header", "data": {"text": "Header"}},
            {"type": "quote", "data": {"caption": "Caption", "text": "Body"}},
            {"type": "list", "data": {"items": ["item 1", "item 2"]}},
        ]
    }

    result = extract_editorjs_text(content)
    assert result == "Header\nCaption\nBody\nitem 1\nitem 2"


def test_update_article_refreshes_updated_at_and_content():
    journal_resp = client.post("/api/journals", json={"title": "Tech Journal"})
    journal_id = journal_resp.json()["id"]

    article_resp = client.post(
        f"/api/journals/{journal_id}/articles",
        json={
            "title": "Initial",
            "content_json": {"blocks": [{"type": "paragraph", "data": {"text": "old"}}]},
        },
    )
    article = article_resp.json()

    patch_resp = client.patch(
        f"/api/articles/{article['id']}",
        json={
            "content_json": {"blocks": [{"type": "paragraph", "data": {"text": "new"}}]},
        },
    )

    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["content_text"] == "new"
    assert updated["updated_at"] >= article["updated_at"]
