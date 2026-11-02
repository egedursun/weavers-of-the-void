import { useSyncExternalStore } from 'react'

const QUERY = '(prefers-reduced-motion: reduce)'
const FORCED_CLASS = 'reduce-motion'

function subscribe(callback: () => void): () => void {
  const media = window.matchMedia(QUERY)
  media.addEventListener('change', callback)
  const observer = new MutationObserver(callback)
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class'],
  })
  return () => {
    media.removeEventListener('change', callback)
    observer.disconnect()
  }
}

function current(): boolean {
  return (
    window.matchMedia(QUERY).matches ||
    document.documentElement.classList.contains(FORCED_CLASS)
  )
}

export function useReducedMotion(): boolean {
  return useSyncExternalStore(subscribe, current, () => false)
}
