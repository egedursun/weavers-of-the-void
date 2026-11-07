import type { ServerEvent } from '@/realtime'
import { beforeEach, describe, expect, it } from 'vitest'
import { forgetWorld, leavesWorld } from './feedWorld'

function hello(world: string | null): ServerEvent {
  return {
    id: 1,
    kind: 'stream.hello',
    payload: { world_key: world },
    at: '',
  } as unknown as ServerEvent
}

describe('leavesWorld', () => {
  beforeEach(() => forgetWorld())

  it('keeps the feed while the server serves the same world', () => {
    expect(leavesWorld(hello('a'))).toBe(false)
    expect(leavesWorld(hello('a'))).toBe(false)
  })

  it('clears the feed when the server comes back with another world', () => {
    expect(leavesWorld(hello('a'))).toBe(false)
    expect(leavesWorld(hello(null))).toBe(true)
    expect(leavesWorld(hello('b'))).toBe(true)
  })

  it('clears the feed when the world is replaced in place', () => {
    const replaced = {
      id: 2,
      kind: 'world.replaced',
      payload: {},
      at: '',
    } as unknown as ServerEvent
    expect(leavesWorld(replaced)).toBe(true)
  })
})
