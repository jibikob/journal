from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

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

client = TestClient(app, headers={"X-User-Id": "1"})


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_journal_list_create_and_get():
    list_resp = client.get('/api/journals')
    assert list_resp.status_code == 200
    assert list_resp.json() == []

    create_resp = client.post('/api/journals', json={'title': 'Backend Journal', 'description': 'notes'})
    assert create_resp.status_code == 201
    created = create_resp.json()

    assert created['title'] == 'Backend Journal'
    assert created['description'] == 'notes'
    assert created['slug'] == 'backend-journal'

    get_resp = client.get(f"/api/journals/{created['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()['id'] == created['id']

    list_after = client.get('/api/journals')
    assert list_after.status_code == 200
    assert [item['id'] for item in list_after.json()] == [created['id']]
