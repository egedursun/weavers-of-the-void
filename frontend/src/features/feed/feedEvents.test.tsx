import { FakeEventSource } from '@/test-utils/fakeEventSource'
import { serverEvent } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { FeedCollector } from './FeedCollector'
import { LiveFeedPanel } from './LiveFeedPanel'
import { INTERRUPTED_TEXT, closeOpenStreams, toFeedLine } from './feedModel'
import { useFeed, useFeedPreferences } from './feedStore'

function lineOf(id: number, kind: string, payload: Record<string, unknown>) {
  const line = toFeedLine(
    serverEvent(kind, { epoch: 4, ...payload }, undefined, id)
  )
  if (!line) throw new Error(`no line for ${kind}`)
  return line
}

function resetFeed() {
  useFeed.setState({
    lines: [],
    restored: true,
    actor: 'all',
    categories: [],
    expanded: [],
  })
  useFeedPreferences.setState({ sounds: false, ambient: false, muted: [] })
}

async function renderFeed() {
  return renderScreen(
    <>
      <FeedCollector />
      <LiveFeedPanel />
    </>,
    { 'GET /api/jobs': [] }
  )
}

beforeEach(resetFeed)
afterEach(resetFeed)

describe('epoch flow lines', () => {
  it('names the son order, the phase, the Fate verdict and the closing time', () => {
    const started = lineOf(1, 'epoch.started', {
      resuming: false,
      order: [
        { id: 1, name: 'Ithren', ini: 14 },
        { id: 2, name: 'Kharun', ini: 9 },
      ],
    })
    expect(started.title).toBe('A new epoch begins')
    expect(started.detail).toBe(
      'Order: Ithren (initiative 14), Kharun (initiative 9)'
    )
    expect(
      lineOf(2, 'epoch.progress', { no: 2, total: 5, name: 'Sons act' }).title
    ).toBe('Phase 2/5: Sons act')
    expect(lineOf(3, 'fate.started', {}).actor).toBe('fate')
    expect(
      lineOf(4, 'fate.step', { text: 'Fate weighs the drowned bell' }).title
    ).toBe('Fate weighs the drowned bell')
    const verdict = lineOf(5, 'fate.finished', {
      rejected: [1],
      corrected: [2, 3],
      fate_debt: false,
    })
    expect(verdict.detail).toBe('1 rejected, 2 corrected.')
    expect(lineOf(6, 'fate.finished', { fate_debt: true }).tone).toBe('warning')
    const closed = lineOf(7, 'epoch.finished', { new_epoch: 5, duration_s: 90 })
    expect(closed.title).toBe('The epoch closed; epoch 5 begins')
    expect(closed.detail).toMatch(/^It took /)
  })
})

describe('mortal agent lines', () => {
  it('lists the waking agents and follows each turn with a link and final words', () => {
    const woke = lineOf(1, 'mortals.started', {
      agents: [
        { entity_id: 40, name: 'Velmora' },
        { entity_id: 41, name: 'Osk' },
      ],
    })
    expect(woke.actor).toBe('mortals')
    expect(woke.title).toBe('2 mortal agents wake')
    expect(woke.detail).toBe('Velmora, Osk')
    const turn = lineOf(2, 'mortal.turn_started', {
      entity_id: 40,
      name: 'Velmora',
    })
    expect(turn.title).toBe('Velmora takes a turn')
    expect(turn.link).toEqual({ kind: 'entity', id: '40', label: 'Velmora' })
    const end = lineOf(3, 'mortal.turn_finished', {
      entity_id: 40,
      name: 'Velmora',
      status: 'success',
      word: 'The salt remembers.',
    })
    expect(end.tone).toBe('success')
    expect(end.detail).toBe('The salt remembers.')
  })
})

describe('job pool lines', () => {
  it('reports queued and started jobs', () => {
    expect(
      lineOf(1, 'job.queued', { job_id: 'a', kind: 'deepen' }).title
    ).toMatch(/queued$/)
    const started = lineOf(2, 'job.started', { job_id: 'a', kind: 'deepen' })
    expect(started.title).toMatch(/started$/)
    expect(started.tone).toBe('primary')
  })
})

describe('world and council lines', () => {
  it('links a born world to its guide and tones a council by its vote', () => {
    const born = lineOf(1, 'world.born', { world_id: 3, name: 'Thessaly' })
    expect(born.title).toBe('Thessaly is born')
    expect(born.link).toEqual({
      kind: 'world-guide',
      id: '3',
      label: 'Thessaly',
    })
    expect(
      lineOf(2, 'council.held', { topic: 'The doom clock', passed: true }).tone
    ).toBe('success')
    expect(
      lineOf(3, 'council.held', { topic: 'The doom clock', passed: false })
        .detail
    ).toBe('The motion failed.')
    expect(lineOf(4, 'genesis.finished', {}).title).toBe('Genesis is complete')
  })
})

describe('dangling stream lines', () => {
  it('closes open writing and thinking lines as interrupted', () => {
    const actor = { actor_kind: 'son', actor_id: 7, actor_name: 'Ithren' }
    const lines = [
      lineOf(1, 'agent.stream', { ...actor, text: 'The tide ', chars: 9 }),
      lineOf(2, 'agent.writing', { stream_id: 's1', chars: 300 }),
      lineOf(3, 'system.note', { text: 'A comet passes' }),
    ]
    const closed = closeOpenStreams(lines)
    expect(closed[0].stream?.phase).toBe('failed')
    expect(closed[0].stream?.text).toBe('The tide ')
    expect(closed[1].stream?.phase).toBe('failed')
    expect(closed[1].stream?.text).toBe(INTERRUPTED_TEXT)
    expect(closed[2]).toBe(lines[2])
    expect(closeOpenStreams(closed)).toBe(closed)
  })

  it('closes them when the stream says hello again', async () => {
    const { emit } = await renderFeed()
    emit('agent.writing', { stream_id: 's9', chars: 120 })
    await expect.poll(() => useFeed.getState().lines.length).toBe(1)
    expect(useFeed.getState().lines[0].stream?.phase).toBe('writing')
    emit('stream.hello', { last_id: 0 })
    await expect
      .poll(() => useFeed.getState().lines[0].stream?.phase)
      .toBe('failed')
  })
})

describe('feed toasts', () => {
  it('toasts a closed epoch, a system error and a council verdict', async () => {
    const { screen, emit } = await renderFeed()
    emit('epoch.finished', { epoch: 4, new_epoch: 5, duration_s: 60 })
    await expect.element(screen.getByText('Epoch 5 began')).toBeInTheDocument()
    emit('system.error', { text: 'The son stumbled on a broken tool' })
    await expect
      .element(screen.getByText('The son stumbled on a broken tool').first())
      .toBeInTheDocument()
    emit('council.held', { topic: 'Who keeps the salt?', passed: true })
    await expect
      .element(screen.getByText('The motion passed.').first())
      .toBeInTheDocument()
  })

  it('stays silent for events from before the page opened', async () => {
    const { screen } = await renderFeed()
    const source = FakeEventSource.latest()
    source.open()
    source.emit(
      'epoch.finished',
      serverEvent(
        'epoch.finished',
        { epoch: 2, new_epoch: 3, duration_s: 5 },
        '2000-01-01T00:00:00Z',
        77
      )
    )
    await expect
      .poll(() =>
        useFeed.getState().lines.some((line) => line.kind === 'epoch.finished')
      )
      .toBe(true)
    expect(screen.getByText('Epoch 3 began').elements()).toHaveLength(0)
  })
})
