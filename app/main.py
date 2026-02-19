from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from sqlalchemy import delete, func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Article, ArticleLink, ArticleSequence, Journal
from .schemas import (
    ArticleCreate,
    ArticleNeighborsOut,
    ArticleOut,
    ArticleSearchOut,
    ArticleUpdate,
    JournalCreate,
    JournalOut,
    JournalUpdate,
    SequenceOut,
    SequenceUpdate,
)
from .utils import extract_editorjs_text, extract_index_entries, extract_wiki_links, slugify

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Journal API")


def sync_article_links(db: Session, article: Article) -> None:
    links = extract_wiki_links(article.content_json)
    for entry in article.index_entries or []:
        article_id = entry.get("article_id")
        if isinstance(article_id, int):
            links.append({"to_article_id": article_id, "anchor": entry.get("title") or f"Article #{article_id}"})

    deduped: dict[tuple[int, str], dict[str, int | str]] = {}
    for link in links:
        key = (link["to_article_id"], link["anchor"])
        deduped[key] = link

    db.execute(delete(ArticleLink).where(ArticleLink.from_article_id == article.id))

    if not deduped:
        return

    rows = [
        {
            "from_article_id": article.id,
            "to_article_id": link["to_article_id"],
            "anchor": link["anchor"],
        }
        for link in deduped.values()
    ]

    insert_stmt = sqlite_insert(ArticleLink).values(rows)
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=["from_article_id", "to_article_id", "anchor"],
        set_={"anchor": insert_stmt.excluded.anchor},
    )
    db.execute(upsert_stmt)


@app.get("/api/journals", response_model=list[JournalOut])
def list_journals(db: Session = Depends(get_db)):
    return db.query(Journal).order_by(Journal.id).all()


@app.post("/api/journals", response_model=JournalOut, status_code=status.HTTP_201_CREATED)
def create_journal(payload: JournalCreate, db: Session = Depends(get_db)):
    slug = payload.slug or slugify(payload.title)
    if db.query(Journal).filter(Journal.slug == slug).first():
        raise HTTPException(status_code=400, detail="Journal slug already exists")

    journal = Journal(title=payload.title, slug=slug, description=payload.description)
    db.add(journal)
    db.commit()
    db.refresh(journal)
    return journal


@app.get("/api/journals/{journal_id}", response_model=JournalOut)
def get_journal(journal_id: int, db: Session = Depends(get_db)):
    journal = db.get(Journal, journal_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    return journal


@app.patch("/api/journals/{journal_id}", response_model=JournalOut)
def update_journal(journal_id: int, payload: JournalUpdate, db: Session = Depends(get_db)):
    journal = db.get(Journal, journal_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")

    if payload.title is not None:
        journal.title = payload.title

    if payload.slug is not None or (payload.slug is None and payload.title is not None):
        new_slug = payload.slug or slugify(journal.title)
        exists = db.query(Journal).filter(Journal.slug == new_slug, Journal.id != journal.id).first()
        if exists:
            raise HTTPException(status_code=400, detail="Journal slug already exists")
        journal.slug = new_slug

    if payload.description is not None:
        journal.description = payload.description

    db.commit()
    db.refresh(journal)
    return journal


@app.delete("/api/journals/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_journal(journal_id: int, db: Session = Depends(get_db)):
    journal = db.get(Journal, journal_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    db.delete(journal)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/journals/{journal_id}/articles", response_model=list[ArticleOut])
def list_articles(journal_id: int, db: Session = Depends(get_db)):
    if not db.get(Journal, journal_id):
        raise HTTPException(status_code=404, detail="Journal not found")
    return db.query(Article).filter(Article.journal_id == journal_id).order_by(Article.id).all()


@app.get("/api/journals/{journal_id}/sequence", response_model=SequenceOut)
def get_journal_sequence(journal_id: int, db: Session = Depends(get_db)):
    if not db.get(Journal, journal_id):
        raise HTTPException(status_code=404, detail="Journal not found")

    rows = (
        db.query(ArticleSequence)
        .filter(ArticleSequence.journal_id == journal_id)
        .order_by(ArticleSequence.position.asc(), ArticleSequence.id.asc())
        .all()
    )
    return SequenceOut(article_ids=[row.article_id for row in rows])


@app.post("/api/journals/{journal_id}/sequence", response_model=SequenceOut)
def set_journal_sequence(journal_id: int, payload: SequenceUpdate, db: Session = Depends(get_db)):
    if not db.get(Journal, journal_id):
        raise HTTPException(status_code=404, detail="Journal not found")

    article_ids = payload.article_ids
    if len(set(article_ids)) != len(article_ids):
        raise HTTPException(status_code=400, detail="Sequence contains duplicate article ids")

    if article_ids:
        count = (
            db.query(Article)
            .filter(Article.journal_id == journal_id, Article.id.in_(article_ids))
            .count()
        )
        if count != len(article_ids):
            raise HTTPException(status_code=400, detail="Sequence contains articles outside the journal")

    db.execute(delete(ArticleSequence).where(ArticleSequence.journal_id == journal_id))
    for index, article_id in enumerate(article_ids):
        db.add(ArticleSequence(journal_id=journal_id, article_id=article_id, position=index))

    db.commit()
    return SequenceOut(article_ids=article_ids)


@app.get("/api/journals/{journal_id}/articles/search", response_model=list[ArticleSearchOut])
def search_articles(journal_id: int, q: str = Query(default=""), db: Session = Depends(get_db)):
    if not db.get(Journal, journal_id):
        raise HTTPException(status_code=404, detail="Journal not found")

    query = db.query(Article).filter(Article.journal_id == journal_id)
    search = q.strip()
    if search:
        like_pattern = f"%{search.lower()}%"
        query = query.filter(func.lower(Article.title).like(like_pattern))

    return query.order_by(Article.updated_at.desc(), Article.id.desc()).limit(20).all()


@app.post(
    "/api/journals/{journal_id}/articles",
    response_model=ArticleOut,
    status_code=status.HTTP_201_CREATED,
)
def create_article(journal_id: int, payload: ArticleCreate, db: Session = Depends(get_db)):
    if not db.get(Journal, journal_id):
        raise HTTPException(status_code=404, detail="Journal not found")

    slug = payload.slug or slugify(payload.title)
    if db.query(Article).filter(Article.slug == slug).first():
        raise HTTPException(status_code=400, detail="Article slug already exists")

    extracted_index_entries = extract_index_entries(payload.content_json)
    article = Article(
        journal_id=journal_id,
        title=payload.title,
        slug=slug,
        content_json=payload.content_json,
        content_text=extract_editorjs_text(payload.content_json),
        is_index=payload.is_index if payload.is_index is not None else bool(extracted_index_entries),
        index_entries=payload.index_entries if payload.index_entries is not None else extracted_index_entries,
        updated_at=datetime.now(timezone.utc),
    )
    db.add(article)
    db.flush()
    sync_article_links(db, article)

    db.commit()
    db.refresh(article)
    return article


@app.get("/api/articles/{article_id}", response_model=ArticleOut)
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@app.patch("/api/articles/{article_id}", response_model=ArticleOut)
def update_article(article_id: int, payload: ArticleUpdate, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if payload.title is not None:
        article.title = payload.title

    if payload.slug is not None or (payload.slug is None and payload.title is not None):
        new_slug = payload.slug or slugify(article.title)
        exists = db.query(Article).filter(Article.slug == new_slug, Article.id != article.id).first()
        if exists:
            raise HTTPException(status_code=400, detail="Article slug already exists")
        article.slug = new_slug

    if payload.content_json is not None:
        article.content_json = payload.content_json
        article.content_text = extract_editorjs_text(payload.content_json)
        extracted_index_entries = extract_index_entries(payload.content_json)
        article.index_entries = payload.index_entries if payload.index_entries is not None else extracted_index_entries
        article.is_index = payload.is_index if payload.is_index is not None else bool(article.index_entries)

    if payload.index_entries is not None:
        article.index_entries = payload.index_entries

    if payload.is_index is not None:
        article.is_index = payload.is_index

    sync_article_links(db, article)
    article.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(article)
    return article


@app.get("/api/articles/{article_id}/neighbors", response_model=ArticleNeighborsOut)
def get_article_neighbors(article_id: int, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    current = (
        db.query(ArticleSequence)
        .filter(ArticleSequence.journal_id == article.journal_id, ArticleSequence.article_id == article_id)
        .first()
    )
    if not current:
        return ArticleNeighborsOut(prev_article_id=None, next_article_id=None)

    prev_entry = (
        db.query(ArticleSequence)
        .filter(
            ArticleSequence.journal_id == article.journal_id,
            ArticleSequence.position == current.position - 1,
        )
        .first()
    )
    next_entry = (
        db.query(ArticleSequence)
        .filter(
            ArticleSequence.journal_id == article.journal_id,
            ArticleSequence.position == current.position + 1,
        )
        .first()
    )

    return ArticleNeighborsOut(
        prev_article_id=prev_entry.article_id if prev_entry else None,
        next_article_id=next_entry.article_id if next_entry else None,
    )


@app.delete("/api/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(article_id: int, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    db.delete(article)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
