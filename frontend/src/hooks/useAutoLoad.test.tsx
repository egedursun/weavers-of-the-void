import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render } from 'vitest-browser-react'
import { useAutoLoad } from './useAutoLoad'

type Seen = (entries: { isIntersecting: boolean }[]) => void

const observers: Seen[] = []

class WatchingObserver {
  constructor(seen: Seen) {
    observers.push(seen)
  }
  observe() {
    observers.at(-1)?.([{ isIntersecting: true }])
  }
  disconnect() {
    return undefined
  }
}

function Feed({ load, enabled }: { load: () => void; enabled: boolean }) {
  const sentinel = useAutoLoad(enabled, load, '600px')
  return <div ref={sentinel} />
}

describe('useAutoLoad', () => {
  beforeEach(() => {
    observers.length = 0
    vi.stubGlobal('IntersectionObserver', WatchingObserver)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('loads once when the sentinel comes into view and never chains loads while it stays there', async () => {
    const first = vi.fn()
    const view = await render(<Feed load={first} enabled />)
    expect(first).toHaveBeenCalledTimes(1)
    const second = vi.fn()
    await view.rerender(<Feed load={second} enabled />)
    const third = vi.fn()
    await view.rerender(<Feed load={third} enabled />)
    expect(observers).toHaveLength(1)
    expect(second).not.toHaveBeenCalled()
    observers[0]([{ isIntersecting: true }])
    expect(third).toHaveBeenCalledTimes(1)
  })

  it('stops watching when there is nothing more to load', async () => {
    const load = vi.fn()
    await render(<Feed load={load} enabled={false} />)
    expect(observers).toHaveLength(0)
    expect(load).not.toHaveBeenCalled()
  })
})
