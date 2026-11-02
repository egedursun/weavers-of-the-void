import { QueryClient } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import { queryKeys } from '@/api/queryKeys'
import { type Job } from '@/api/system'
import { EVENT_KINDS, type ServerEvent } from './events'
import {
  INVALIDATIONS,
  applyServerEvent,
  invalidationsFor,
} from './invalidation'

const AT = '2026-01-01T00:00:00+00:00'

const job: Job = {
  id: 'a',
  kind: 'epoch',
  status: 'running',
  progress: 0.1,
  stage: null,
  params: {},
  result: null,
  error: null,
  created_at: AT,
  started_at: AT,
  finished_at: null,
  label: null,
  items: [],
}

describe('query invalidation', () => {
  it('has a rule for every event kind', () => {
    expect(Object.keys(INVALIDATIONS).sort()).toEqual([...EVENT_KINDS].sort())
  })

  it('invalidates the job and the health after a job finishes', () => {
    const event: ServerEvent = {
      id: 1,
      kind: 'job.finished',
      payload: { job_id: 'a', kind: 'epoch', result: null },
      at: AT,
    }
    expect(invalidationsFor(event)).toEqual([
      queryKeys.jobs.all,
      queryKeys.jobs.detail('a'),
      queryKeys.health,
    ])
  })

  it('invalidates world queries when the world changes', async () => {
    const client = new QueryClient()
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    applyServerEvent(client, {
      id: 2,
      kind: 'world.changed',
      payload: {},
      at: AT,
    })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.world.all })
  })

  it('patches job progress in place without refetching', () => {
    const client = new QueryClient()
    client.setQueryData(queryKeys.jobs.detail('a'), job)
    client.setQueryData(queryKeys.jobs.list(5), [job])
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    applyServerEvent(client, {
      id: 3,
      kind: 'job.progress',
      payload: {
        job_id: 'a',
        kind: 'epoch',
        progress: 0.75,
        stage: 'Fate judges',
      },
      at: AT,
    })
    expect(client.getQueryData<Job>(queryKeys.jobs.detail('a'))?.progress).toBe(
      0.75
    )
    expect(client.getQueryData<Job[]>(queryKeys.jobs.list(5))?.[0].stage).toBe(
      'Fate judges'
    )
    expect(invalidate).not.toHaveBeenCalled()
  })
})
