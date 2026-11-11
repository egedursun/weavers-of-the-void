import { type ThreeEvent } from '@react-three/fiber'
import { describe, expect, it, vi } from 'vitest'
import { TAP_SLOP, onTap } from './sceneTap'

function pointerUp(delta: number) {
  const stopPropagation = vi.fn()
  return {
    event: { delta, stopPropagation } as unknown as ThreeEvent<MouseEvent>,
    stopPropagation,
  }
}

describe('scene tap', () => {
  it('acts on a click that stayed in place', () => {
    const act = vi.fn()
    const { event, stopPropagation } = pointerUp(1)
    onTap(act)(event)
    expect(act).toHaveBeenCalledWith(event)
    expect(stopPropagation).toHaveBeenCalled()
  })

  it('ignores the click that ends a drag', () => {
    const act = vi.fn()
    const { event, stopPropagation } = pointerUp(TAP_SLOP + 40)
    onTap(act)(event)
    expect(act).not.toHaveBeenCalled()
    expect(stopPropagation).toHaveBeenCalled()
  })
})
