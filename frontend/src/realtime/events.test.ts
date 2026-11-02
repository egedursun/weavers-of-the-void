import { serverEvent } from '@/test-utils/fakeEventSource'
import { describe, expect, it } from 'vitest'
import { EVENT_KINDS, parseServerEvent } from './events'

describe('parseServerEvent', () => {
  it('parses a typed job progress event', () => {
    const event = parseServerEvent(
      JSON.stringify(
        serverEvent(4, 'job.progress', {
          job_id: 'a',
          kind: 'epoch',
          progress: 0.5,
          stage: null,
        })
      )
    )
    expect(event?.kind).toBe('job.progress')
    expect(event?.id).toBe(4)
  })

  it('rejects unknown kinds, broken JSON and malformed payloads', () => {
    expect(
      parseServerEvent(JSON.stringify(serverEvent(1, 'dragon.woke', {})))
    ).toBeNull()
    expect(parseServerEvent('{not json')).toBeNull()
    expect(
      parseServerEvent(
        JSON.stringify(
          serverEvent(1, 'job.failed', { job_id: 'a', kind: 'epoch' })
        )
      )
    ).toBeNull()
  })

  it('knows every backend event kind from the generated schema', () => {
    expect(EVENT_KINDS).toContain('job.progress')
    expect(EVENT_KINDS).toContain('epoch.finished')
    expect(new Set(EVENT_KINDS).size).toBe(EVENT_KINDS.length)
  })
})
