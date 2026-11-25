import { type ServerEvent } from '@/realtime'
import { describe, expect, it } from 'vitest'
import { appendLines, buildRows, toFeedLine } from './feedModel'

const AT = '2026-01-01T12:00:00+00:00'

function event(
  id: number,
  kind: string,
  payload: Record<string, unknown>
): ServerEvent {
  return { id, kind, payload, at: AT } as unknown as ServerEvent
}

const ACTOR = { actor_kind: 'son', actor_id: 7, actor_name: 'Ithren' }

function lineOf(id: number, kind: string, payload: Record<string, unknown>) {
  const line = toFeedLine(event(id, kind, { ...ACTOR, ...payload }))
  if (!line) throw new Error('no line')
  return line
}

describe('stream lines', () => {
  it('leaves the Divine Will stream to its own panel', () => {
    for (const kind of ['agent.stream', 'agent.thought', 'agent.tool_call']) {
      const willEvent = event(9, kind, {
        ...ACTOR,
        actor_kind: 'creator',
        channel: 'divine_will:12',
        text: 'The plan is written.',
      })
      expect(toFeedLine(willEvent)).toBeNull()
    }
    expect(
      toFeedLine(event(10, 'agent.thought', { ...ACTOR, text: 'Plain.' }))
    ).not.toBeNull()
  })

  it('joins streamed text into one line and closes it with the thought', () => {
    const lines = appendLines(
      [],
      [
        lineOf(1, 'agent.stream', { text: 'The tide ', chars: 9 }),
        lineOf(2, 'agent.stream', { text: 'turns.', chars: 15 }),
      ]
    )
    expect(lines).toHaveLength(1)
    expect(lines[0].stream?.text).toBe('The tide turns.')
    const closed = appendLines(lines, [
      lineOf(3, 'agent.thought', { text: 'The tide turns, and I follow.' }),
    ])
    expect(closed).toHaveLength(1)
    expect(closed[0].stream?.phase).toBe('thought')
    const next = appendLines(closed, [
      lineOf(4, 'agent.stream', { text: 'Again.', chars: 6 }),
    ])
    expect(next).toHaveLength(2)
  })

  it('follows one tool call from preparing to result in place', () => {
    const call = { call_id: 'c1', tool: 'create_place' }
    let lines = appendLines([], [lineOf(1, 'agent.tool_preparing', call)])
    lines = appendLines(lines, [
      lineOf(2, 'agent.tool_writing', { ...call, chars: 400 }),
    ])
    lines = appendLines(lines, [
      lineOf(3, 'agent.tool_called', { ...call, read_only: false }),
    ])
    lines = appendLines(lines, [
      lineOf(4, 'agent.tool_result', {
        ...call,
        text: 'Made.',
        error: false,
        quiet: false,
      }),
    ])
    expect(lines).toHaveLength(1)
    expect(lines[0].stream?.phase).toBe('result')
    expect(lines[0].stream?.chars).toBe(400)
    expect(lines[0].stream?.text).toBe('Made.')
  })

  it('groups consecutive read-only calls of one actor', () => {
    const lines = appendLines(
      [],
      ['a', 'b', 'c'].flatMap((id, index) => [
        lineOf(index * 2 + 1, 'agent.tool_called', {
          call_id: id,
          tool: 'read_place',
          read_only: true,
        }),
      ])
    )
    const rows = buildRows(lines, new Set())
    expect(rows).toHaveLength(1)
    expect(rows[0].type).toBe('reading')
  })

  it('tracks a long write by its stream id', () => {
    const write = { stream_id: 'w1', who: 'The chronicler' }
    const base = { actor_kind: 'system' }
    let lines = appendLines(
      [],
      [
        toFeedLine(
          event(1, 'agent.writing', {
            ...base,
            ...write,
            chars: 500,
            finished: false,
          })
        )!,
      ]
    )
    lines = appendLines(lines, [
      toFeedLine(
        event(2, 'agent.writing', {
          ...base,
          ...write,
          chars: 900,
          finished: true,
          status: 'ok',
        })
      )!,
    ])
    expect(lines).toHaveLength(1)
    expect(lines[0].stream?.phase).toBe('finished')
    expect(lines[0].stream?.chars).toBe(900)
  })
})

describe('turn details', () => {
  it('shows the model chip and rarity the server sends on a turn', () => {
    const line = toFeedLine(
      event(1, 'son.turn_started', {
        son_id: 7,
        son_name: 'Ithren',
        resumed: false,
        model: 'claude-haiku-5-5',
        rarity: 'rare',
      })
    )
    expect(line?.meta.chips).toEqual(['claude-haiku-5-5'])
    expect(line?.meta.rarity).toBe('rare')
  })

  it('marks a successful finished turn as a success', () => {
    const line = toFeedLine(
      event(3, 'son.turn_finished', {
        son_id: 7,
        son_name: 'Ithren',
        status: 'success',
        creations: [],
        model: 'claude-haiku-5-5',
        rarity: 'rare',
      })
    )
    expect(line?.tone).toBe('success')
    expect(line?.meta.rarity).toBe('rare')
  })

  it('describes a model call retry with its wait', () => {
    const line = toFeedLine(
      event(4, 'agent.retry', {
        actor: 'fate',
        kind: 'model_call',
        attempt: 2,
        total: 3,
        wait_s: 6,
        kept_steps: 0,
      })
    )
    expect(line?.meta.chips).toEqual(['Model call retried', 'waits 6s'])
  })

  it('describes a continuation retry with the kept steps', () => {
    const line = toFeedLine(
      event(2, 'agent.retry', {
        actor: 'Ithren',
        kind: 'continuation',
        attempt: 1,
        total: 3,
        kept_steps: 4,
        wait_s: 8,
      })
    )
    expect(line?.meta.chips).toEqual([
      'Resumed where it stopped',
      '4 successful steps kept',
      'waits 8s',
    ])
  })
})
