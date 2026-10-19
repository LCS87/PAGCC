/** Cliente HTTP leve sobre fetch, com token JWT e erros padronizados. */

export const TOKEN_KEY = 'pagcc.token'
export const USER_KEY = 'pagcc.user'

export class ApiError extends Error {
  status: number
  code: string
  details?: unknown

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

export type QueryValue = string | number | boolean | null | undefined

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  body?: unknown
  query?: Record<string, QueryValue | QueryValue[]>
  signal?: AbortSignal
  responseType?: 'json' | 'blob'
}

function apiBase(): string {
  const configured = import.meta.env.VITE_API_BASE_URL ?? ''
  return configured.replace(/\/$/, '')
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const url = `${apiBase()}${path}`
  if (!query) return url
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === null || value === undefined || value === '') continue
    if (Array.isArray(value)) {
      for (const entry of value) {
        if (entry === null || entry === undefined || entry === '') continue
        params.append(key, String(entry))
      }
    } else {
      params.append(key, String(value))
    }
  }
  const serialized = params.toString()
  return serialized ? `${url}?${serialized}` : url
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

function expireSession(): void {
  setToken(null)
  window.dispatchEvent(new CustomEvent('auth:expired'))
}

async function parseError(response: Response): Promise<ApiError> {
  let code = 'http_error'
  let message = `Falha na requisição (HTTP ${response.status}).`
  let details: unknown
  try {
    const payload = (await response.json()) as {
      error?: { code?: string; message?: string; details?: unknown }
    }
    if (payload?.error) {
      code = payload.error.code ?? code
      message = payload.error.message ?? message
      details = payload.error.details
    }
  } catch {
    // resposta sem corpo JSON
  }
  return new ApiError(response.status, code, message, details)
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(buildUrl(path, options.query), {
      method: options.method ?? 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    })
  } catch (error) {
    if ((error as Error).name === 'AbortError') throw error
    throw new ApiError(0, 'network_error', 'Não foi possível conectar à API. Verifique o servidor.')
  }

  if (!response.ok) {
    if (response.status === 401 && token) expireSession()
    throw await parseError(response)
  }

  if (options.responseType === 'blob') {
    return (await response.blob()) as T
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'POST', body }),
  patch: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'PATCH', body }),
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return 'Erro inesperado. Tente novamente.'
}
