import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { IDLE_QUIET_MS } from '@/constants/ui'
import { noteActivity, pendingCount, resetIdleGate, whenIdle } from './idleGate'

describe('idle gate', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    resetIdleGate()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('runs at once when the player is idle', () => {
    const run = vi.fn()
    whenIdle('a', run)
    expect(run).toHaveBeenCalledTimes(1)
  })

  it('defers while the player is active and runs once after the quiet period', () => {
    const run = vi.fn()
    noteActivity()
    whenIdle('a', run)
    whenIdle('a', run)
    expect(run).not.toHaveBeenCalled()
    expect(pendingCount()).toBe(1)
    vi.advanceTimersByTime(IDLE_QUIET_MS + 10)
    expect(run).toHaveBeenCalledTimes(1)
    expect(pendingCount()).toBe(0)
  })

  it('keeps waiting while activity continues', () => {
    const run = vi.fn()
    noteActivity()
    whenIdle('a', run)
    vi.advanceTimersByTime(IDLE_QUIET_MS - 100)
    noteActivity()
    vi.advanceTimersByTime(IDLE_QUIET_MS - 100)
    expect(run).not.toHaveBeenCalled()
    vi.advanceTimersByTime(300)
    expect(run).toHaveBeenCalledTimes(1)
  })
})
