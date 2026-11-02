import { type ServerEvent } from '@/realtime'
import { beforeEach, describe, expect, it } from 'vitest'
import {
  IMAGE_LINES_KEPT,
  percentOf,
  stageText,
  useImageGenStore,
} from './imageGenState'

const FUTURE = '2999-01-01T00:00:00+00:00'
const REPLAYED = '2000-01-01T00:00:00+00:00'

function event(
  id: number,
  kind: string,
  payload: unknown,
  at = FUTURE
): ServerEvent {
  return { id, kind, payload, at } as unknown as ServerEvent
}

function reset() {
  useImageGenStore.setState({ since: Date.now(), progress: {}, lines: [] })
}

describe('image generation state', () => {
  beforeEach(reset)

  it('tracks a queued image with the number of jobs ahead', () => {
    useImageGenStore
      .getState()
      .record(event(1, 'image.queued', { node_id: 4, position: 2 }))
    useImageGenStore
      .getState()
      .record(event(2, 'image.queued', { node_id: 5, position: 0 }))
    const texts = useImageGenStore.getState().lines.map((line) => line.text)
    expect(texts).toEqual(['Queued', 'Queued, 2 ahead'])
  })

  it('updates one line in place while progress arrives and records the percent', () => {
    const { record } = useImageGenStore.getState()
    record(
      event(1, 'image.progress', { node_id: 4, stage: 'loading', percent: 10 })
    )
    record(
      event(2, 'image.progress', { node_id: 4, stage: 'steps', percent: 62.4 })
    )
    const state = useImageGenStore.getState()
    expect(state.lines).toHaveLength(1)
    expect(state.lines[0]).toMatchObject({
      nodeId: 4,
      tone: 'progress',
      text: 'Painting · 62%',
    })
    expect(state.progress[4]).toEqual({ stage: 'steps', percent: 62.4 })
  })

  it('finishes with a file and clears the running progress', () => {
    const { record } = useImageGenStore.getState()
    record(
      event(1, 'image.progress', { node_id: 4, stage: 'steps', percent: 90 })
    )
    record(event(2, 'image.done', { node_id: 4, file: 'a.png' }))
    const state = useImageGenStore.getState()
    expect(state.progress[4]).toBeUndefined()
    expect(state.lines[0]).toMatchObject({
      tone: 'done',
      file: 'a.png',
      text: 'Image finished',
    })
  })

  it('shows the failure message and clears progress', () => {
    const { record } = useImageGenStore.getState()
    record(
      event(1, 'image.progress', { node_id: 4, stage: 'steps', percent: 20 })
    )
    record(event(2, 'image.failed', { node_id: 4, error: 'Out of memory' }))
    const state = useImageGenStore.getState()
    expect(state.progress[4]).toBeUndefined()
    expect(state.lines[0]).toMatchObject({
      tone: 'failed',
      text: 'Out of memory',
    })
  })

  it('keeps bulk log lines apart and ignores empty ones', () => {
    const { record } = useImageGenStore.getState()
    record(event(1, 'image.bulk_log', { text: 'Batch 1 of 3' }))
    record(event(2, 'image.bulk_log', { text: '' }))
    const state = useImageGenStore.getState()
    expect(state.lines).toHaveLength(1)
    expect(state.lines[0]).toMatchObject({
      tone: 'bulk',
      nodeId: null,
      text: 'Batch 1 of 3',
    })
  })

  it('never changes state for replayed history events', () => {
    const { record } = useImageGenStore.getState()
    record(
      event(
        1,
        'image.progress',
        { node_id: 4, stage: 'steps', percent: 50 },
        REPLAYED
      )
    )
    record(event(2, 'image.done', { node_id: 4, file: 'a.png' }, REPLAYED))
    const state = useImageGenStore.getState()
    expect(state.lines).toEqual([])
    expect(state.progress).toEqual({})
  })

  it('caps the number of kept lines', () => {
    const { record } = useImageGenStore.getState()
    for (let node = 1; node <= IMAGE_LINES_KEPT + 5; node += 1)
      record(event(node, 'image.queued', { node_id: node, position: 0 }))
    expect(useImageGenStore.getState().lines).toHaveLength(IMAGE_LINES_KEPT)
  })

  it('names stages and clamps the ring percent', () => {
    expect(stageText('steps')).toBe('Painting')
    expect(stageText('custom')).toBe('custom')
    expect(stageText(null)).toBe('Working')
    expect(percentOf({ phase: 'running', stage: 'steps', percent: 140 })).toBe(
      100
    )
    expect(percentOf({ phase: 'idle' })).toBe(0)
    expect(percentOf({ phase: 'queued', ahead: 1 })).toBe(0)
  })
})
