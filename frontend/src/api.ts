export type Journal = {
  id: number
  title: string
  slug: string
  description: string | null
}

export type Article = {
  id: number
  journal_id: number
  title: string
  slug: string
  content_json: Record<string, unknown>
  content_text: string
  is_index: boolean
  index_entries: Array<{ article_id: number; title?: string }>
  updated_at: string
}

export type ArticleSearchResult = {
  id: number
  title: string
  content_text: string
}

export type ArticleNeighbors = {
  prev_article_id: number | null
  next_article_id: number | null
}

export type ArticleSequence = {
  article_ids: number[]
}

export type ApiError = {
  detail?: string
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const data = (await response.json()) as ApiError
      if (data?.detail) {
        detail = data.detail
      }
    } catch {
      // ignore non-json error payloads
    }
    throw new Error(detail)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export const api = {
  listJournals: () => request<Journal[]>('/journals'),
  createJournal: (payload: { title: string; slug?: string; description?: string }) =>
    request<Journal>('/journals', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getJournal: (journalId: number) => request<Journal>(`/journals/${journalId}`),
  listJournalArticles: (journalId: number) => request<Article[]>(`/journals/${journalId}/articles`),

  getJournalSequence: (journalId: number) => request<ArticleSequence>(`/journals/${journalId}/sequence`),
  updateJournalSequence: (journalId: number, articleIds: number[]) =>
    request<ArticleSequence>(`/journals/${journalId}/sequence`, {
      method: 'POST',
      body: JSON.stringify({ article_ids: articleIds }),
    }),
  searchJournalArticles: (journalId: number, query: string) =>
    request<ArticleSearchResult[]>(`/journals/${journalId}/articles/search?q=${encodeURIComponent(query)}`),
  createArticle: (
    journalId: number,
    payload: { title: string; slug?: string; content_json?: Record<string, unknown> },
  ) =>
    request<Article>(`/journals/${journalId}/articles`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getArticle: (articleId: number) => request<Article>(`/articles/${articleId}`),
  getArticleNeighbors: (articleId: number) => request<ArticleNeighbors>(`/articles/${articleId}/neighbors`),
  updateArticle: (
    articleId: number,
    payload: { title?: string; slug?: string; content_json?: Record<string, unknown> },
  ) =>
    request<Article>(`/articles/${articleId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
}
