import { API_VERSION, type ApiEnvelope, type DraftRevision, type RunResult, type ValidationResult } from '../types'

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly details?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export interface SimulationApi {
  saveDraft(draft: DraftRevision, signal?: AbortSignal): Promise<DraftRevision>
  loadDraft(draftId: string, signal?: AbortSignal): Promise<DraftRevision>
  validateDraft(draft: DraftRevision, signal?: AbortSignal): Promise<ValidationResult>
  runDraft(draft: DraftRevision, signal?: AbortSignal): Promise<RunResult>
}

export class V1AlphaClient implements SimulationApi {
  constructor(
    private readonly baseUrl = `/api/${API_VERSION}`,
    private readonly fetcher: typeof fetch = fetch,
  ) {}

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    let response: Response
    try {
      response = await this.fetcher(`${this.baseUrl}${path}`, {
        ...init,
        headers: { 'Content-Type': 'application/json', Accept: 'application/json', ...init.headers },
      })
    } catch (error) {
      throw new ApiError('The simulation service is unavailable.', undefined, error)
    }

    const body = await response.json().catch(() => undefined) as ApiEnvelope<T> | undefined
    if (!response.ok) {
      throw new ApiError(`Simulation service returned ${response.status}.`, response.status, body)
    }
    if (!body || body.apiVersion !== API_VERSION) {
      throw new ApiError('The simulation service returned an incompatible response.', response.status, body)
    }
    return body.data
  }

  saveDraft(draft: DraftRevision, signal?: AbortSignal) {
    return this.request<DraftRevision>(`/drafts/${draft.draftId}`, {
      method: 'PUT', body: JSON.stringify(draft), signal,
    })
  }

  loadDraft(draftId: string, signal?: AbortSignal) {
    return this.request<DraftRevision>(`/drafts/${draftId}`, { method: 'GET', signal })
  }

  validateDraft(draft: DraftRevision, signal?: AbortSignal) {
    return this.request<ValidationResult>(`/drafts/${draft.draftId}/validate`, {
      method: 'POST', body: JSON.stringify(draft), signal,
    })
  }

  runDraft(draft: DraftRevision, signal?: AbortSignal) {
    return this.request<RunResult>(`/drafts/${draft.draftId}/runs`, {
      method: 'POST', body: JSON.stringify(draft), signal,
    })
  }
}
