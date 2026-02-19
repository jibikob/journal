import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from 'react'
import { api, Article, ArticleSearchResult, Journal } from './api'
import './styles.css'

type OutputData = {
  blocks: Array<Record<string, unknown>>
  time?: number
  version?: string
}

type WikiLinkConfig = {
  journalId: number
}

type IndexEntry = {
  articleId: number
  title: string
}

type EditorApi = {
  selection: {
    findParentTag: (tagName: string) => HTMLElement | null
    expandToTag: (element: HTMLElement) => void
  }
}

type EditorInlineTool = {
  render: () => HTMLElement
  surround: (range: Range) => void
  checkState: () => void
}

type EditorInstance = {
  save: () => Promise<OutputData>
  destroy: () => Promise<void> | void
}

type EditorBlockTool = {
  render: () => HTMLElement
  save: (blockContent: HTMLElement) => Record<string, unknown>
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
    ImageTool?: unknown
  }
}

class WikiLinkInlineTool implements EditorInlineTool {
  static isInline = true
  static title = 'Link to article'

  private readonly api: EditorApi
  private readonly config: WikiLinkConfig
  private button: HTMLButtonElement | null = null

  constructor({ api: editorApi, config }: { api: EditorApi; config: WikiLinkConfig }) {
    this.api = editorApi
    this.config = config
  }

  render(): HTMLElement {
    this.button = document.createElement('button')
    this.button.type = 'button'
    this.button.classList.add('cdx-settings-button')
    this.button.textContent = 'Wiki'
    return this.button
  }

  async surround(range: Range): Promise<void> {
    if (!range || range.collapsed) {
      return
    }

    const selectedText = range.toString().trim()
    if (!selectedText) {
      return
    }

    const query = window.prompt('Search article', selectedText)
    if (query === null) {
      return
    }

    const results = await api.searchJournalArticles(this.config.journalId, query)
    if (results.length === 0) {
      window.alert('No articles found')
      return
    }

    const picked = this.pickArticle(results)
    if (!picked) {
      return
    }

    const anchor = document.createElement('a')
    anchor.dataset.articleId = String(picked.id)
    anchor.dataset.articleTitle = picked.title
    anchor.href = `/articles/${picked.id}`
    anchor.className = 'wiki-link'
    anchor.textContent = selectedText

    const extracted = range.extractContents()
    if (!extracted.textContent?.trim()) {
      return
    }

    range.insertNode(anchor)
    this.api.selection.expandToTag(anchor)
  }

  checkState(): void {
    const anchorTag = this.api.selection.findParentTag('A')
    if (!this.button) {
      return
    }
    this.button.classList.toggle('cdx-settings-button--active', Boolean(anchorTag?.dataset.articleId))
  }

  private pickArticle(results: ArticleSearchResult[]): ArticleSearchResult | null {
    const optionsText = results
      .slice(0, 10)
      .map((item, index) => `${index + 1}. ${item.title} (#${item.id})`)
      .join('\n')

    const selectedRaw = window.prompt(`Pick article number:\n${optionsText}`)
    if (!selectedRaw) {
      return null
    }

    const selectedIndex = Number(selectedRaw) - 1
    if (!Number.isInteger(selectedIndex) || selectedIndex < 0 || selectedIndex >= Math.min(results.length, 10)) {
      window.alert('Invalid selection')
      return null
    }

    return results[selectedIndex]
  }
}


class IndexListTool implements EditorBlockTool {
  static toolbox = {
    title: 'IndexList',
    icon: '<svg width="18" height="18" viewBox="0 0 18 18"><path d="M3 4h12v2H3V4Zm0 4h12v2H3V8Zm0 4h12v2H3v-2Z"/></svg>',
  }

  private readonly journalId: number
  private readonly data: { entries?: IndexEntry[] }

  constructor({ config, data }: { config: WikiLinkConfig; data: { entries?: IndexEntry[] } }) {
    this.journalId = config.journalId
    this.data = data || {}
  }

  render(): HTMLElement {
    const wrapper = document.createElement('div')
    wrapper.className = 'index-tool'

    const entries = this.data.entries || []
    const list = document.createElement('ul')
    list.className = 'index-tool-list'

    const renderItems = () => {
      list.innerHTML = ''
      entries.forEach((entry) => {
        const li = document.createElement('li')
        li.textContent = `${entry.title} (#${entry.articleId})`
        list.appendChild(li)
      })
    }

    const addButton = document.createElement('button')
    addButton.type = 'button'
    addButton.className = 'index-tool-button'
    addButton.textContent = 'Добавить ссылку'
    addButton.onclick = async () => {
      const query = window.prompt('Search article')
      if (!query) {
        return
      }
      const results = await api.searchJournalArticles(this.journalId, query)
      if (results.length === 0) {
        window.alert('No articles found')
        return
      }
      const selected = window.prompt(
        `Pick article number:
${results
          .slice(0, 10)
          .map((item, index) => `${index + 1}. ${item.title} (#${item.id})`)
          .join('\n')}`,
      )
      if (!selected) {
        return
      }
      const selectedIndex = Number(selected) - 1
      if (!Number.isInteger(selectedIndex) || selectedIndex < 0 || selectedIndex >= Math.min(results.length, 10)) {
        window.alert('Invalid selection')
        return
      }
      const picked = results[selectedIndex]
      entries.push({ articleId: picked.id, title: picked.title })
      renderItems()
    }

    renderItems()
    wrapper.appendChild(addButton)
    wrapper.appendChild(list)
    return wrapper
  }

  save(blockContent: HTMLElement): Record<string, unknown> {
    const entries = Array.from(blockContent.querySelectorAll('li')).map((item) => {
      const match = item.textContent?.match(/^(.*) \(#(\d+)\)$/)
      if (!match) {
        return null
      }
      return { articleId: Number(match[2]), title: match[1] }
    })
    return { entries: entries.filter(Boolean) }
  }
}

const EDITOR_SCRIPTS = [
  'https://cdn.jsdelivr.net/npm/@editorjs/editorjs@2.30.8/dist/editorjs.umd.min.js',
  'https://cdn.jsdelivr.net/npm/@editorjs/header@2.8.8/dist/header.umd.min.js',
  'https://cdn.jsdelivr.net/npm/@editorjs/list@2.0.8/dist/list.umd.min.js',
  'https://cdn.jsdelivr.net/npm/@editorjs/quote@2.7.6/dist/quote.umd.min.js',
  'https://cdn.jsdelivr.net/npm/@editorjs/delimiter@1.4.2/dist/delimiter.umd.min.js',
  'https://cdn.jsdelivr.net/npm/@editorjs/paragraph@2.11.6/dist/paragraph.umd.min.js',
  'https://cdn.jsdelivr.net/npm/@editorjs/image@2.10.3/dist/image.umd.min.js',
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

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\$&')
}

function renderHighlightedText(text: string, query: string): ReactNode {
  const search = query.trim()
  if (!search) {
    return text
  }

  const pattern = new RegExp(`(${escapeRegExp(search)})`, 'ig')
  const parts = text.split(pattern)

  return parts.map((part, index) =>
    part.toLowerCase() === search.toLowerCase() ? <mark key={`${part}-${index}`}>{part}</mark> : part,
  )
}

function JournalsPage() { /* unchanged */
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
      await api.createJournal({ title, slug: slug || undefined, description: description || undefined })
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
      <section className="card"><h2>Создать журнал</h2><form onSubmit={onSubmit} className="form-grid"><label>Название<input value={title} onChange={(e) => setTitle(e.target.value)} required /></label><label>Slug<input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="optional" /></label><label>Описание<textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} /></label><button disabled={submitting}>{submitting ? 'Создание...' : 'Создать'}</button></form></section>
      <section className="card"><h2>Список журналов</h2>{loading && <p className="info">Загрузка...</p>}{error && <p className="error">Ошибка: {error}</p>}{!loading && journals.length === 0 && <p className="info">Пока журналов нет.</p>}<ul className="list">{journals.map((journal) => (<li key={journal.id}><AppLink href={`/journals/${journal.id}`}>{journal.title}</AppLink><span className="muted"> / {journal.slug}</span></li>))}</ul></section>
    </div>
  )
}

function JournalDetailsPage({ journalId }: { journalId: number }) {
  const [journal, setJournal] = useState<Journal | null>(null)
  const [articles, setArticles] = useState<Article[]>([])
  const [sequenceIds, setSequenceIds] = useState<number[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [sequenceMode, setSequenceMode] = useState(false)
  const [savingSequence, setSavingSequence] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<ArticleSearchResult[]>([])
  const [searching, setSearching] = useState(false)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [journalResponse, articlesResponse, sequenceResponse] = await Promise.all([
        api.getJournal(journalId),
        api.listJournalArticles(journalId),
        api.getJournalSequence(journalId),
      ])
      setJournal(journalResponse)
      setArticles(articlesResponse)
      setSequenceIds(sequenceResponse.article_ids)
    } catch (loadError) {
      setError((loadError as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [journalId])

  const sequenceArticles = useMemo(() => {
    const byId = new Map(articles.map((item) => [item.id, item]))
    const ordered = sequenceIds
      .map((id) => byId.get(id))
      .filter((item): item is Article => Boolean(item))
    const missing = articles.filter((item) => !sequenceIds.includes(item.id))
    return [...ordered, ...missing]
  }, [articles, sequenceIds])

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await api.createArticle(journalId, { title, slug: slug || undefined, content_json: { text: content } })
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

  const moveSequenceItem = (index: number, direction: -1 | 1) => {
    setSequenceIds((current) => {
      const orderedIds = [
        ...current.filter((id) => articles.some((article) => article.id === id)),
        ...articles.map((article) => article.id).filter((id) => !current.includes(id)),
      ]
      const nextIndex = index + direction
      if (index < 0 || index >= orderedIds.length || nextIndex < 0 || nextIndex >= orderedIds.length) {
        return orderedIds
      }
      const copy = [...orderedIds]
      const [moved] = copy.splice(index, 1)
      copy.splice(nextIndex, 0, moved)
      return copy
    })
  }

  const saveSequence = async () => {
    setSavingSequence(true)
    setError(null)
    try {
      const result = await api.updateJournalSequence(
        journalId,
        sequenceArticles.map((article) => article.id),
      )
      setSequenceIds(result.article_ids)
    } catch (sequenceError) {
      setError((sequenceError as Error).message)
    } finally {
      setSavingSequence(false)
    }
  }

  const onSearchSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSearching(true)
    setError(null)
    try {
      const results = await api.searchJournalArticles(journalId, searchQuery)
      setSearchResults(results)
    } catch (searchError) {
      setError((searchError as Error).message)
    } finally {
      setSearching(false)
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
            <h2>Поиск по статьям</h2>
            <form onSubmit={onSearchSubmit} className="form-grid search-form">
              <label>
                Запрос
                <input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Искать по заголовку и тексту"
                />
              </label>
              <button type="submit" disabled={searching}>{searching ? 'Поиск...' : 'Найти'}</button>
            </form>

            {searchQuery.trim() && !searching && searchResults.length === 0 && (
              <p className="info">Ничего не найдено.</p>
            )}

            {searchResults.length > 0 && (
              <ul className="search-results">
                {searchResults.map((article) => (
                  <li key={article.id}>
                    <AppLink href={`/articles/${article.id}`}>
                      {renderHighlightedText(article.title, searchQuery)}
                    </AppLink>
                    <p className="muted search-snippet">
                      {renderHighlightedText((article.content_text || '').slice(0, 180), searchQuery)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card">
            <div className="sequence-header">
              <h2>Статьи</h2>
              <button type="button" onClick={() => setSequenceMode((value) => !value)}>
                {sequenceMode ? 'Обычный список' : 'Sequence editor'}
              </button>
            </div>

            {articles.length === 0 && <p className="info">Пока статей нет.</p>}
            {!sequenceMode && (
              <ul className="list">
                {articles.map((article) => (
                  <li key={article.id}>
                    <AppLink href={`/articles/${article.id}`}>{article.title}</AppLink>
                    <span className="muted"> / {article.slug}</span>
                  </li>
                ))}
              </ul>
            )}

            {sequenceMode && (
              <div className="sequence-editor">
                <ul className="sequence-list">
                  {sequenceArticles.map((article, index) => (
                    <li key={article.id}>
                      <span>{index + 1}. {article.title}</span>
                      <div className="sequence-actions">
                        <button type="button" onClick={() => moveSequenceItem(index, -1)} disabled={index === 0}>↑</button>
                        <button
                          type="button"
                          onClick={() => moveSequenceItem(index, 1)}
                          disabled={index === sequenceArticles.length - 1}
                        >
                          ↓
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
                <button type="button" onClick={saveSequence} disabled={savingSequence || sequenceArticles.length === 0}>
                  {savingSequence ? 'Сохранение...' : 'Сохранить порядок'}
                </button>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}


function renderBlockHtml(
  block: Record<string, unknown>,
  articleTitleById: Record<number, string>,
  articlePreviewById: Record<number, string>,
): string {
  const type = (block.type as string) ?? 'paragraph'
  const data = (block.data as Record<string, unknown>) ?? {}
  const rawText = typeof data.text === 'string' ? data.text : ''

  const parser = new DOMParser()
  const doc = parser.parseFromString(`<div>${rawText}</div>`, 'text/html')
  doc.querySelectorAll('a[data-article-id]').forEach((anchor) => {
    const articleId = Number(anchor.getAttribute('data-article-id'))
    if (!Number.isFinite(articleId)) {
      return
    }
    const title = articleTitleById[articleId] || `Статья #${articleId}`
    anchor.setAttribute('href', `/articles/${articleId}`)
    anchor.setAttribute('target', '_blank')
    anchor.setAttribute('rel', 'noopener noreferrer')
    const preview = articlePreviewById[articleId]
    anchor.setAttribute('data-tooltip', preview ? `${title}\n${preview}` : title)
    anchor.classList.add('wiki-link')
  })


  if (type === 'indexList') {
    const entries = Array.isArray(data.entries) ? (data.entries as Array<Record<string, unknown>>) : []
    const listItems = entries
      .map((entry) => {
        const id = typeof entry.articleId === 'number' ? entry.articleId : Number(entry.articleId)
        if (!Number.isFinite(id)) {
          return ''
        }
        const title = articleTitleById[id] || (typeof entry.title === 'string' ? entry.title : `Статья #${id}`)
        const preview = articlePreviewById[id]
        const tooltip = preview ? `${title}\n${preview}` : title
        return `<li><a class="wiki-link" data-tooltip="${tooltip.replace(/"/g, '&quot;')}" href="/articles/${id}" target="_blank" rel="noopener noreferrer">${title}</a></li>`
      })
      .filter(Boolean)
      .join('')

    return `<ul class="index-list-view">${listItems}</ul>`
  }

  const html = doc.body.firstElementChild?.innerHTML ?? rawText
  if (type === 'header') {
    return `<h3>${html}</h3>`
  }
  return `<p>${html}</p>`
}

function ArticleViewPage({ articleId }: { articleId: number }) {
  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [articleTitleById, setArticleTitleById] = useState<Record<number, string>>({})
  const [articlePreviewById, setArticlePreviewById] = useState<Record<number, string>>({})
  const [neighbors, setNeighbors] = useState<{ prev_article_id: number | null; next_article_id: number | null }>({
    prev_article_id: null,
    next_article_id: null,
  })

  useEffect(() => {
    const loadArticle = async () => {
      setLoading(true)
      setError(null)
      try {
        const loadedArticle = await api.getArticle(articleId)
        setArticle(loadedArticle)
        const [relatedArticles, neighborResponse] = await Promise.all([
          api.listJournalArticles(loadedArticle.journal_id),
          api.getArticleNeighbors(articleId),
        ])
        setNeighbors(neighborResponse)
        setArticleTitleById(Object.fromEntries(relatedArticles.map((item) => [item.id, item.title])))
        setArticlePreviewById(
          Object.fromEntries(
            relatedArticles.map((item) => [item.id, (item.content_text || '').split('\n').slice(0, 2).join(' ')]),
          ),
        )
      } catch (loadError) {
        setError((loadError as Error).message)
      } finally {
        setLoading(false)
      }
    }

    void loadArticle()
  }, [articleId])

  const blockHtml = useMemo(() => {
    if (!article) {
      return []
    }

    const contentJson = article.content_json as OutputData
    if (!contentJson?.blocks) {
      return []
    }

    return contentJson.blocks.map((block, index) => ({
      id: index,
      html: renderBlockHtml(block, articleTitleById, articlePreviewById),
    }))
  }, [article, articleTitleById, articlePreviewById])

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
          {blockHtml.length > 0 ? (
            <div className="content-rich">
              {blockHtml.map((block) => (
                <div key={block.id} dangerouslySetInnerHTML={{ __html: block.html }} />
              ))}
            </div>
          ) : (
            <pre className="content">{article.content_text || JSON.stringify(article.content_json, null, 2)}</pre>
          )}
          <div className="neighbors-nav">
            {neighbors.prev_article_id ? <AppLink href={`/articles/${neighbors.prev_article_id}`}>← Prev</AppLink> : <span />}
            {neighbors.next_article_id ? <AppLink href={`/articles/${neighbors.next_article_id}`}>Next →</AppLink> : null}
          </div>
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
    if (loading || !contentJson || !journalId) {
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
            paragraph: { class: window.Paragraph, inlineToolbar: true },
            header: { class: window.Header, inlineToolbar: true },
            list: { class: window.List, inlineToolbar: true },
            quote: { class: window.Quote, inlineToolbar: true },
            delimiter: window.Delimiter,
            image: {
              class: window.ImageTool,
              config: {
                uploader: {
                  uploadByFile: async (file: File) => {
                    const result = await api.uploadImage(file)
                    return {
                      success: 1,
                      file: { url: result.url },
                    }
                  },
                },
              },
            },
            wikilink: { class: WikiLinkInlineTool, config: { journalId } },
            indexList: { class: IndexListTool, config: { journalId } },
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
  }, [loading, contentJson, editorHolderId, journalId])

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
