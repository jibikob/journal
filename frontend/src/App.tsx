import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from 'react'
import { api, Article, Journal } from './api'
import './styles.css'

type OutputData = {
  blocks: Array<Record<string, unknown>>
  time?: number
  version?: string
}

type EditorInstance = {
  save: () => Promise<OutputData>
  destroy: () => Promise<void> | void
}

type EditorConstructor = new (config: {
  holder: string
  data: OutputData
  tools: Record<string, unknown>
  onChange: () => void
}) => EditorInstance

declare global {
  interface Window {
    EditorJS?: EditorConstructor
    Header?: unknown
    List?: unknown
    Quote?: unknown
    Delimiter?: unknown
    Paragraph?: unknown
  }
}

const EDITOR_SCRIPTS = [
  'https://cdn.jsdelivr.net/npm/@editorjs/editorjs@2.30.8/dist/editorjs.umd.min.js',
  'https://cdn.jsdelivr.net/npm/@editorjs/header@2.8.8/dist/header.umd.min.js',
  'https://cdn.jsdelivr.net/npm/@editorjs/list@2.0.8/dist/list.umd.min.js',
  'https://cdn.jsdelivr.net/npm/@editorjs/quote@2.7.6/dist/quote.umd.min.js',
  'https://cdn.jsdelivr.net/npm/@editorjs/delimiter@1.4.2/dist/delimiter.umd.min.js',
  'https://cdn.jsdelivr.net/npm/@editorjs/paragraph@2.11.6/dist/paragraph.umd.min.js',
]

let editorScriptsPromise: Promise<void> | null = null
let navigationGuard: (() => boolean) | null = null

function loadEditorScripts(): Promise<void> {
  if (editorScriptsPromise) {
    return editorScriptsPromise
  }

  editorScriptsPromise = EDITOR_SCRIPTS.reduce((chain, url) => {
    return chain.then(
      () =>
        new Promise<void>((resolve, reject) => {
          if (document.querySelector(`script[data-editorjs-src="${url}"]`)) {
            resolve()
            return
          }

          const script = document.createElement('script')
          script.src = url
          script.async = true
          script.dataset.editorjsSrc = url
          script.onload = () => resolve()
          script.onerror = () => reject(new Error(`Failed to load ${url}`))
          document.head.appendChild(script)
        }),
    )
  }, Promise.resolve())

  return editorScriptsPromise
}

function setNavigationGuard(guard: (() => boolean) | null): void {
  navigationGuard = guard
}

function canLeavePage(): boolean {
  return navigationGuard ? navigationGuard() : true
}

type Route =
  | { name: 'journals' }
  | { name: 'journalDetails'; journalId: number }
  | { name: 'articleView'; articleId: number }
  | { name: 'articleEdit'; articleId: number }

function parsePath(pathname: string): Route {
  const parts = pathname.split('/').filter(Boolean)

  if (parts.length === 1 && parts[0] === 'journals') {
    return { name: 'journals' }
  }

  if (parts.length === 2 && parts[0] === 'journals') {
    const journalId = Number(parts[1])
    if (Number.isFinite(journalId)) {
      return { name: 'journalDetails', journalId }
    }
  }

  if (parts.length === 2 && parts[0] === 'articles') {
    const articleId = Number(parts[1])
    if (Number.isFinite(articleId)) {
      return { name: 'articleView', articleId }
    }
  }

  if (parts.length === 3 && parts[0] === 'articles' && parts[2] === 'edit') {
    const articleId = Number(parts[1])
    if (Number.isFinite(articleId)) {
      return { name: 'articleEdit', articleId }
    }
  }

  return { name: 'journals' }
}

function navigate(path: string): void {
  if (window.location.pathname === path) {
    return
  }
  if (!canLeavePage()) {
    return
  }
  window.history.pushState({}, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

function AppLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a
      href={href}
      onClick={(event) => {
        event.preventDefault()
        navigate(href)
      }}
    >
      {children}
    </a>
  )
}

function JournalsPage() {
  const [journals, setJournals] = useState<Journal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const loadJournals = async () => {
    setLoading(true)
    setError(null)
    try {
      setJournals(await api.listJournals())
    } catch (loadError) {
      setError((loadError as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadJournals()
  }, [])

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)

    try {
      await api.createJournal({
        title,
        slug: slug || undefined,
        description: description || undefined,
      })
      setTitle('')
      setSlug('')
      setDescription('')
      await loadJournals()
    } catch (submitError) {
      setError((submitError as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page">
      <h1>Журналы</h1>
      <section className="card">
        <h2>Создать журнал</h2>
        <form onSubmit={onSubmit} className="form-grid">
          <label>
            Название
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label>
            Slug
            <input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="optional" />
          </label>
          <label>
            Описание
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
          </label>
          <button disabled={submitting}>{submitting ? 'Создание...' : 'Создать'}</button>
        </form>
      </section>

      <section className="card">
        <h2>Список журналов</h2>
        {loading && <p className="info">Загрузка...</p>}
        {error && <p className="error">Ошибка: {error}</p>}
        {!loading && journals.length === 0 && <p className="info">Пока журналов нет.</p>}
        <ul className="list">
          {journals.map((journal) => (
            <li key={journal.id}>
              <AppLink href={`/journals/${journal.id}`}>{journal.title}</AppLink>
              <span className="muted"> / {journal.slug}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

function JournalDetailsPage({ journalId }: { journalId: number }) {
  const [journal, setJournal] = useState<Journal | null>(null)
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [journalResponse, articlesResponse] = await Promise.all([
        api.getJournal(journalId),
        api.listJournalArticles(journalId),
      ])
      setJournal(journalResponse)
      setArticles(articlesResponse)
    } catch (loadError) {
      setError((loadError as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [journalId])

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)

    try {
      await api.createArticle(journalId, {
        title,
        slug: slug || undefined,
        content_json: { text: content },
      })
      setTitle('')
      setSlug('')
      setContent('')
      await loadData()
    } catch (submitError) {
      setError((submitError as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page">
      <p>
        <AppLink href="/journals">← К журналам</AppLink>
      </p>

      {loading && <p className="info">Загрузка...</p>}
      {error && <p className="error">Ошибка: {error}</p>}

      {journal && (
        <>
          <section className="card">
            <h1>{journal.title}</h1>
            <p className="muted">/{journal.slug}</p>
            <p>{journal.description || 'Нет описания'}</p>
          </section>

          <section className="card">
            <h2>Создать статью</h2>
            <form onSubmit={onSubmit} className="form-grid">
              <label>
                Заголовок
                <input value={title} onChange={(e) => setTitle(e.target.value)} required />
              </label>
              <label>
                Slug
                <input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="optional" />
              </label>
              <label>
                Текст
                <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={5} />
              </label>
              <button disabled={submitting}>{submitting ? 'Создание...' : 'Создать статью'}</button>
            </form>
          </section>

          <section className="card">
            <h2>Статьи</h2>
            {articles.length === 0 && <p className="info">Пока статей нет.</p>}
            <ul className="list">
              {articles.map((article) => (
                <li key={article.id}>
                  <AppLink href={`/articles/${article.id}`}>{article.title}</AppLink>
                  <span className="muted"> / {article.slug}</span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  )
}

function ArticleViewPage({ articleId }: { articleId: number }) {
  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadArticle = async () => {
      setLoading(true)
      setError(null)
      try {
        setArticle(await api.getArticle(articleId))
      } catch (loadError) {
        setError((loadError as Error).message)
      } finally {
        setLoading(false)
      }
    }

    void loadArticle()
  }, [articleId])

  return (
    <div className="page">
      {article && (
        <p>
          <AppLink href={`/journals/${article.journal_id}`}>← К журналу</AppLink>
        </p>
      )}
      {loading && <p className="info">Загрузка...</p>}
      {error && <p className="error">Ошибка: {error}</p>}

      {article && (
        <section className="card">
          <h1>{article.title}</h1>
          <p className="muted">/{article.slug}</p>
          <pre className="content">{article.content_text || JSON.stringify(article.content_json, null, 2)}</pre>
          <p>
            <AppLink href={`/articles/${article.id}/edit`}>Редактировать статью</AppLink>
          </p>
        </section>
      )}
    </div>
  )
}

function ArticleEditPage({ articleId }: { articleId: number }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [savedMessage, setSavedMessage] = useState<string | null>(null)

  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [contentJson, setContentJson] = useState<OutputData | null>(null)
  const [updatedAt, setUpdatedAt] = useState<string | null>(null)
  const [journalId, setJournalId] = useState<number | null>(null)

  const editorRef = useRef<EditorInstance | null>(null)
  const hasUnsavedChangesRef = useRef(false)
  const editorHolderId = `editorjs-${articleId}`

  const markUnsaved = () => {
    hasUnsavedChangesRef.current = true
    setSavedMessage(null)
  }

  useEffect(() => {
    const loadArticle = async () => {
      setLoading(true)
      setError(null)
      try {
        const loaded = await api.getArticle(articleId)
        setTitle(loaded.title)
        setSlug(loaded.slug)
        setContentJson(loaded.content_json as OutputData)
        setUpdatedAt(loaded.updated_at)
        setJournalId(loaded.journal_id)
        hasUnsavedChangesRef.current = false
      } catch (loadError) {
        setError((loadError as Error).message)
      } finally {
        setLoading(false)
      }
    }

    void loadArticle()
  }, [articleId])

  useEffect(() => {
    if (loading || !contentJson) {
      return
    }

    let disposed = false
    let localEditor: EditorInstance | null = null

    const init = async () => {
      try {
        await loadEditorScripts()
        if (disposed || !window.EditorJS) {
          return
        }

        localEditor = new window.EditorJS({
          holder: editorHolderId,
          data: contentJson,
          tools: {
            paragraph: window.Paragraph,
            header: window.Header,
            list: window.List,
            quote: window.Quote,
            delimiter: window.Delimiter,
          },
          onChange: markUnsaved,
        })

        editorRef.current = localEditor
      } catch (initError) {
        setError((initError as Error).message)
      }
    }

    void init()

    return () => {
      disposed = true
      editorRef.current = null
      if (localEditor) {
        void localEditor.destroy()
      }
    }
  }, [loading, contentJson, editorHolderId])

  useEffect(() => {
    const guard = () => {
      if (!hasUnsavedChangesRef.current) {
        return true
      }
      return window.confirm('У вас есть несохраненные изменения. Покинуть страницу?')
    }

    setNavigationGuard(guard)

    const beforeUnloadHandler = (event: BeforeUnloadEvent) => {
      if (!hasUnsavedChangesRef.current) {
        return
      }
      event.preventDefault()
      event.returnValue = ''
    }

    window.addEventListener('beforeunload', beforeUnloadHandler)

    return () => {
      if (navigationGuard === guard) {
        setNavigationGuard(null)
      }
      window.removeEventListener('beforeunload', beforeUnloadHandler)
    }
  }, [])

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)

    try {
      const contentForSave = editorRef.current ? await editorRef.current.save() : { blocks: [] }
      const updated = await api.updateArticle(articleId, {
        title,
        slug,
        content_json: contentForSave,
      })
      setUpdatedAt(updated.updated_at)
      setSavedMessage('Saved')
      setContentJson(updated.content_json as OutputData)
      hasUnsavedChangesRef.current = false
    } catch (submitError) {
      setError((submitError as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page">
      {journalId && (
        <p>
          <AppLink href={`/journals/${journalId}`}>← К журналу</AppLink>
        </p>
      )}
      {loading && <p className="info">Загрузка...</p>}
      {error && <p className="error">Ошибка: {error}</p>}

      {!loading && (
        <section className="card">
          <h1>Редактирование статьи</h1>
          <form className="form-grid" onSubmit={onSubmit}>
            <label>
              Заголовок
              <input
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value)
                  markUnsaved()
                }}
                required
              />
            </label>
            <label>
              Slug
              <input
                value={slug}
                onChange={(e) => {
                  setSlug(e.target.value)
                  markUnsaved()
                }}
                required
              />
            </label>
            <div>
              Контент
              <div id={editorHolderId} className="editor" />
            </div>
            <button disabled={submitting || loading}>{submitting ? 'Сохранение...' : 'Save'}</button>
            {savedMessage && <p className="success">{savedMessage}</p>}
            {updatedAt && <p className="muted">Updated at: {new Date(updatedAt).toLocaleString()}</p>}
          </form>
        </section>
      )}
    </div>
  )
}

export default function App() {
  const [pathname, setPathname] = useState(window.location.pathname)
  const pathnameRef = useRef(pathname)

  useEffect(() => {
    pathnameRef.current = pathname
  }, [pathname])

  useEffect(() => {
    if (window.location.pathname === '/') {
      navigate('/journals')
    }

    const handlePopState = () => {
      if (!canLeavePage()) {
        window.history.pushState({}, '', pathnameRef.current)
        return
      }
      setPathname(window.location.pathname)
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const route = useMemo(() => parsePath(pathname), [pathname])

  return (
    <main className="layout">
      {route.name === 'journals' && <JournalsPage />}
      {route.name === 'journalDetails' && <JournalDetailsPage journalId={route.journalId} />}
      {route.name === 'articleView' && <ArticleViewPage articleId={route.articleId} />}
      {route.name === 'articleEdit' && <ArticleEditPage articleId={route.articleId} />}
    </main>
  )
}
