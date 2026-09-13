import { describe, expect, it, vi } from 'vitest'
import { API_VERSION, type DraftRevision, type ValidationResult } from '../types'
import { ApiError, V1AlphaClient } from './client'

const draft: DraftRevision = { schemaVersion: API_VERSION, draftId: 'draft-1', revision: 1, baseCaseId: null, updatedAt: '2026-08-27T00:00:00Z', nodes: [], edges: [] }

describe('V1AlphaClient', () => {
  it('calls the versioned validation endpoint', async () => {
    const result: ValidationResult = { valid: true, degreesOfFreedom: 0, diagnostics: [] }
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ apiVersion: API_VERSION, data: result }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    const client = new V1AlphaClient('/api/v1alpha', fetcher)
    await expect(client.validateDraft(draft)).resolves.toEqual(result)
    expect(fetcher).toHaveBeenCalledWith('/api/v1alpha/drafts/draft-1/validate', expect.objectContaining({ method: 'POST' }))
  })

  it('rejects responses from an incompatible API version', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ apiVersion: 'v2', data: {} }), { status: 200 }))
    await expect(new V1AlphaClient('/api/v1alpha', fetcher).validateDraft(draft)).rejects.toBeInstanceOf(ApiError)
  })

  it('loads the latest persisted draft', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ apiVersion: API_VERSION, data: draft }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    const client = new V1AlphaClient('/api/v1alpha', fetcher)
    await expect(client.loadDraft('draft-1')).resolves.toEqual(draft)
    expect(fetcher).toHaveBeenCalledWith('/api/v1alpha/drafts/draft-1', expect.objectContaining({ method: 'GET' }))
  })
})
