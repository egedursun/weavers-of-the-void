import { describe, expect, it, vi } from 'vitest'
import { createEventBus } from './eventBus'
import { type ServerEvent } from './events'

const rulesChanged: ServerEvent = {
  id: 1,
  kind: 'rules.changed',
  payload: {},
  at: '2026-01-01T00:00:00+00:00',
}

describe('event bus', () => {
  it('delivers events by kind and to catch-all listeners', () => {
    const bus = createEventBus()
    const onRules = vi.fn()
    const onWorld = vi.fn()
    const onAny = vi.fn()
    bus.on('rules.changed', onRules)
    bus.on('world.changed', onWorld)
    bus.onAny(onAny)
    bus.emit(rulesChanged)
    expect(onRules).toHaveBeenCalledWith(rulesChanged)
    expect(onWorld).not.toHaveBeenCalled()
    expect(onAny).toHaveBeenCalledOnce()
  })

  it('stops delivering after unsubscribe', () => {
    const bus = createEventBus()
    const handler = vi.fn()
    const unsubscribe = bus.on('rules.changed', handler)
    unsubscribe()
    bus.emit(rulesChanged)
    expect(handler).not.toHaveBeenCalled()
  })
})
