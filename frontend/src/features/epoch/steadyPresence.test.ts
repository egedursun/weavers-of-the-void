import { describe, expect, it } from 'vitest'
import { HIDE_AFTER_MS, SHOW_AFTER_MS, nextPresence } from './steadyPresence'

describe('steady presence', () => {
  it('waits before showing so a blink of work never flashes the strip', () => {
    let presence = nextPresence({ shown: false, since: null }, true, 0)
    expect(presence.shown).toBe(false)
    presence = nextPresence(presence, false, SHOW_AFTER_MS / 2)
    expect(presence).toEqual({ shown: false, since: null })
    presence = nextPresence(presence, true, 1000)
    presence = nextPresence(presence, true, 1000 + SHOW_AFTER_MS)
    expect(presence.shown).toBe(true)
  })

  it('lingers after the work ends so jobs in a row read as one steady strip', () => {
    let presence = nextPresence({ shown: true, since: null }, false, 0)
    expect(presence.shown).toBe(true)
    presence = nextPresence(presence, true, HIDE_AFTER_MS / 2)
    expect(presence).toEqual({ shown: true, since: null })
    presence = nextPresence(presence, false, 5000)
    presence = nextPresence(presence, false, 5000 + HIDE_AFTER_MS)
    expect(presence.shown).toBe(false)
  })
})
