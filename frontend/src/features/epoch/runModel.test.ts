import { type ServerEvent } from '@/realtime'
import { describe, expect, it } from 'vitest'
import {
  IDLE_RUN,
  STALE_RUN_MS,
  applyRunEvent,
  isStaleRun,
  phaseRatio,
} from './runModel'

function event(
  kind: string,
  payload: Record<string, unknown>,
  at = '2026-01-01T12:00:00Z'
): ServerEvent {
  return { id: 1, kind, payload, at } as unknown as ServerEvent
}

describe('epoch run model', () => {
  it('follows an epoch from start to close', () => {
    let state = applyRunEvent(
      IDLE_RUN,
      event('epoch.started', { epoch: 4, resuming: false })
    )
    expect(state.active).toBe(true)
    state = applyRunEvent(
      state,
      event('epoch.progress', {
        epoch: 4,
        no: 2,
        total: 5,
        name: 'Engine',
      })
    )
    expect(phaseRatio(state.phase)).toBeCloseTo(0.4)
    state = applyRunEvent(
      state,
      event('engine.phase', { epoch: 4, phase: 'warfare', seconds: 1.5 })
    )
    expect(state.phases).toEqual([
      { name: 'warfare', seconds: 1.5, failed: false },
    ])
    state = applyRunEvent(state, event('epoch.stop_requested', {}))
    expect(state.stopRequested).toBe(true)
    state = applyRunEvent(
      state,
      event('epoch.finished', { epoch: 4, new_epoch: 5, duration_s: 60 })
    )
    expect(state.active).toBe(false)
    expect(state.last?.newEpoch).toBe(5)
    expect(state.last?.phases).toHaveLength(1)
  })

  it('records where a stopped epoch halted', () => {
    const started = applyRunEvent(
      IDLE_RUN,
      event(
        'epoch.started',
        { epoch: 2, resuming: false },
        '2026-01-01T12:00:00Z'
      )
    )
    const stopped = applyRunEvent(
      started,
      event('epoch.stopped', { epoch: 2, phase: 3 }, '2026-01-01T12:01:00Z')
    )
    expect(stopped.last?.stoppedAtPhase).toBe(3)
    expect(stopped.last?.durationSeconds).toBe(60)
  })

  it('ignores actor events outside a run', () => {
    const state = applyRunEvent(
      IDLE_RUN,
      event('son.turn_started', { son_id: 1, son_name: 'A', resumed: false })
    )
    expect(state).toBe(IDLE_RUN)
  })
})

describe('a run replayed from before a restart', () => {
  it('is stale once the server says no epoch is running', () => {
    const state = applyRunEvent(
      IDLE_RUN,
      event('epoch.started', { epoch: 7, resuming: false })
    )
    const started = state.startedAt ?? 0
    expect(isStaleRun(state, false, started + STALE_RUN_MS + 1)).toBe(true)
    expect(isStaleRun(state, true, started + STALE_RUN_MS + 1)).toBe(false)
    expect(isStaleRun(state, false, started + 1)).toBe(false)
    expect(isStaleRun(state, undefined, started + STALE_RUN_MS + 1)).toBe(false)
    expect(isStaleRun(IDLE_RUN, false, started + STALE_RUN_MS + 1)).toBe(false)
  })
})
