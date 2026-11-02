import { FakeEventSource, serverEvent } from '@/test-utils/fakeEventSource'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EventStream, retryDelay, type StreamStatus } from './eventStream'

const CONNECTING = 0
const CLOSED = 2

function setup() {
  const scheduled: { callback: () => void; delay: number }[] = []
  const statuses: StreamStatus[] = []
  const onEvent = vi.fn()
  const onResync = vi.fn()
  const stream = new EventStream({
    url: '/api/events',
    onEvent,
    onResync,
    onStatus: (status) => statuses.push(status),
    createSource: (url) => new FakeEventSource(url),
    retryBaseMs: 100,
    retryMaxMs: 400,
    schedule: (callback, delay) => {
      scheduled.push({ callback, delay })
      return () => undefined
    },
  })
  return { stream, scheduled, statuses, onEvent, onResync }
}

describe('EventStream', () => {
  beforeEach(() => FakeEventSource.reset())

  it('opens one source and dispatches parsed events in order without duplicates', () => {
    const { stream, onEvent, statuses } = setup()
    stream.start()
    stream.start()
    expect(FakeEventSource.instances).toHaveLength(1)
    const source = FakeEventSource.latest()
    source.open()
    source.emit(
      'job.queued',
      serverEvent(1, 'job.queued', { job_id: 'a', kind: 'epoch' })
    )
    source.emit(
      'job.queued',
      serverEvent(1, 'job.queued', { job_id: 'a', kind: 'epoch' })
    )
    source.emit('world.changed', serverEvent(2, 'world.changed', {}))
    expect(onEvent).toHaveBeenCalledTimes(2)
    expect(stream.lastEventId).toBe(2)
    expect(statuses).toEqual(['connecting', 'open'])
  })

  it('lets the browser resume with Last-Event-ID while it is still connecting', () => {
    const { stream, scheduled, statuses } = setup()
    stream.start()
    FakeEventSource.latest().fail(CONNECTING)
    expect(scheduled).toHaveLength(0)
    expect(FakeEventSource.instances).toHaveLength(1)
    expect(statuses.at(-1)).toBe('reconnecting')
  })

  it('reconnects with exponential backoff after a hard failure and asks for a resync', () => {
    const { stream, scheduled, onResync } = setup()
    stream.start()
    FakeEventSource.latest().fail(CLOSED)
    expect(scheduled[0].delay).toBe(100)
    scheduled[0].callback()
    expect(FakeEventSource.instances).toHaveLength(2)
    FakeEventSource.latest().fail(CLOSED)
    expect(scheduled[1].delay).toBe(200)
    scheduled[1].callback()
    FakeEventSource.latest().open()
    expect(onResync).toHaveBeenCalledOnce()
  })

  it('closes the source when stopped and ignores late errors', () => {
    const { stream, scheduled, statuses } = setup()
    stream.start()
    const source = FakeEventSource.latest()
    stream.stop()
    expect(source.closed).toBe(true)
    source.fail(CLOSED)
    expect(scheduled).toHaveLength(0)
    expect(statuses.at(-1)).toBe('closed')
  })

  it('caps the retry delay', () => {
    expect(retryDelay(0, 100, 400)).toBe(100)
    expect(retryDelay(5, 100, 400)).toBe(400)
  })
})
