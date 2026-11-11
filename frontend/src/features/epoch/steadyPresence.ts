import { useEffect, useState } from 'react'

export const SHOW_AFTER_MS = 700
export const HIDE_AFTER_MS = 2500

export type Presence = { shown: boolean; since: number | null }

export function nextPresence(
  presence: Presence,
  wanted: boolean,
  now: number
): Presence {
  if (wanted === presence.shown) return { shown: presence.shown, since: null }
  const since = presence.since ?? now
  const wait = wanted ? SHOW_AFTER_MS : HIDE_AFTER_MS
  return now - since >= wait
    ? { shown: wanted, since: null }
    : { shown: presence.shown, since }
}

export function useSteadyPresence<T>(
  wanted: boolean,
  value: T
): { shown: boolean; value: T } {
  const [presence, setPresence] = useState<Presence>({
    shown: false,
    since: null,
  })
  const key = JSON.stringify(value)
  const [kept, setKept] = useState({ key, value })
  if (wanted && key !== kept.key) setKept({ key, value })
  useEffect(() => {
    const step = () =>
      setPresence((current) => nextPresence(current, wanted, Date.now()))
    step()
    if (wanted === presence.shown) return
    const timer = window.setTimeout(
      step,
      wanted ? SHOW_AFTER_MS : HIDE_AFTER_MS
    )
    return () => window.clearTimeout(timer)
  }, [wanted, presence.shown])
  return { shown: presence.shown, value: wanted ? value : kept.value }
}
