import { useEffect, useRef } from 'react'

export function useAutoLoad(
  enabled: boolean,
  load: () => void,
  margin: string
) {
  const sentinel = useRef<HTMLDivElement>(null)
  const latest = useRef(load)
  useEffect(() => {
    latest.current = load
  })
  useEffect(() => {
    const element = sentinel.current
    if (!element || !enabled || typeof IntersectionObserver === 'undefined')
      return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) latest.current()
      },
      { rootMargin: margin }
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [enabled, margin])
  return sentinel
}
