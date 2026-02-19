from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.utils import extract_editorjs_text, extract_index_entries, extract_wiki_links

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


def test_extract_wiki_links():
    content = {
        "blocks": [
            {
                "type": "paragraph",
                "data": {
                    "text": '<a data-article-id="2">Target 2</a> and <a data-article-id="3">Target 3</a>'
                },
            }
        ]
    }

    assert extract_wiki_links(content) == [
        {"to_article_id": 2, "anchor": "Target 2"},
        {"to_article_id": 3, "anchor": "Target 3"},
    ]


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
            "content_json": {
                "blocks": [
                    {
                        "type": "paragraph",
                        "data": {"text": '<a data-article-id="999">new anchor</a>'},
                    }
                ]
            },
        },
    )

    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["content_text"] == "new anchor"
    assert updated["updated_at"] >= article["updated_at"]

    with engine.connect() as conn:
        links = conn.execute(text("SELECT from_article_id, to_article_id, anchor FROM article_links")).fetchall()

    assert len(links) == 1
    assert links[0][1] == 999
    assert links[0][2] == "new anchor"


def test_search_articles_endpoint_returns_ranked_matches_from_title_and_content():
    journal_resp = client.post("/api/journals", json={"title": "Search Journal"})
    journal_id = journal_resp.json()["id"]

    title_match = client.post(
        f"/api/journals/{journal_id}/articles",
        json={"title": "Alpha title", "content_json": {"blocks": [{"type": "paragraph", "data": {"text": "misc"}}]}},
    ).json()
    content_match = client.post(
        f"/api/journals/{journal_id}/articles",
        json={
            "title": "Gamma",
            "content_json": {"blocks": [{"type": "paragraph", "data": {"text": "contains alpha token"}}]},
        },
    ).json()

    other_journal = client.post("/api/journals", json={"title": "Other Journal"}).json()
    client.post(f"/api/journals/{other_journal['id']}/articles", json={"title": "Alpha Other"})

    response = client.get(f"/api/journals/{journal_id}/articles/search?q=alpha")
    assert response.status_code == 200

    data = response.json()
    assert [item["id"] for item in data] == [title_match["id"], content_match["id"]]
    assert data[0]["title"] == "Alpha title"
    assert "alpha" in data[1]["content_text"].lower()


def test_extract_index_entries():
    content = {
        "blocks": [
            {
                "type": "indexList",
                "data": {"entries": [{"articleId": 2, "title": "Target 2"}, {"articleId": 3, "title": "Target 3"}]},
            }
        ]
    }

    assert extract_index_entries(content) == [
        {"article_id": 2, "title": "Target 2"},
        {"article_id": 3, "title": "Target 3"},
    ]


def test_index_blocks_set_is_index_and_sync_links():
    journal_resp = client.post("/api/journals", json={"title": "Index Journal"})
    journal_id = journal_resp.json()["id"]

    article_resp = client.post(
        f"/api/journals/{journal_id}/articles",
        json={
            "title": "Index page",
            "content_json": {
                "blocks": [
                    {
                        "type": "indexList",
                        "data": {"entries": [{"articleId": 123, "title": "Entry 123"}]},
                    }
                ]
            },
        },
    )
    assert article_resp.status_code == 201
    data = article_resp.json()
    assert data["is_index"] is True
    assert data["index_entries"] == [{"article_id": 123, "title": "Entry 123"}]

    with engine.connect() as conn:
        links = conn.execute(text("SELECT from_article_id, to_article_id FROM article_links")).fetchall()

    assert len(links) == 1
    assert links[0][1] == 123


def test_article_sequence_set_get_and_neighbors():
    journal_id = client.post("/api/journals", json={"title": "Sequence Journal"}).json()["id"]

    article_a = client.post(f"/api/journals/{journal_id}/articles", json={"title": "A"}).json()
    article_b = client.post(f"/api/journals/{journal_id}/articles", json={"title": "B"}).json()
    article_c = client.post(f"/api/journals/{journal_id}/articles", json={"title": "C"}).json()

    set_resp = client.post(
        f"/api/journals/{journal_id}/sequence",
        json={"article_ids": [article_b["id"], article_a["id"], article_c["id"]]},
    )
    assert set_resp.status_code == 200
    assert set_resp.json()["article_ids"] == [article_b["id"], article_a["id"], article_c["id"]]

    get_resp = client.get(f"/api/journals/{journal_id}/sequence")
    assert get_resp.status_code == 200
    assert get_resp.json()["article_ids"] == [article_b["id"], article_a["id"], article_c["id"]]

    first_neighbors = client.get(f"/api/articles/{article_b['id']}/neighbors").json()
    middle_neighbors = client.get(f"/api/articles/{article_a['id']}/neighbors").json()
    last_neighbors = client.get(f"/api/articles/{article_c['id']}/neighbors").json()

    assert first_neighbors == {"prev_article_id": None, "next_article_id": article_a["id"]}
    assert middle_neighbors == {"prev_article_id": article_b["id"], "next_article_id": article_c["id"]}
    assert last_neighbors == {"prev_article_id": article_a["id"], "next_article_id": None}


def test_article_sequence_rejects_foreign_or_duplicate_ids():
    journal_id = client.post("/api/journals", json={"title": "Main Journal"}).json()["id"]
    other_journal_id = client.post("/api/journals", json={"title": "Other Journal"}).json()["id"]

    own_article = client.post(f"/api/journals/{journal_id}/articles", json={"title": "Own"}).json()
    foreign_article = client.post(f"/api/journals/{other_journal_id}/articles", json={"title": "Foreign"}).json()

    duplicate_resp = client.post(
        f"/api/journals/{journal_id}/sequence",
        json={"article_ids": [own_article["id"], own_article["id"]]},
    )
    assert duplicate_resp.status_code == 400

    foreign_resp = client.post(
        f"/api/journals/{journal_id}/sequence",
        json={"article_ids": [own_article["id"], foreign_article["id"]]},
    )
    assert foreign_resp.status_code == 400
