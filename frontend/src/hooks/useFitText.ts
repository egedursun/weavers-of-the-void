import { useLayoutEffect, useRef } from 'react'

export const FIT_LEVELS = 4

export function useFitText<E extends HTMLElement>(content: unknown) {
  const ref = useRef<E>(null)
  useLayoutEffect(() => {
    const element = ref.current
    if (!element) return
    const fit = () => {
      for (let level = 0; level < FIT_LEVELS; level += 1) {
        element.dataset.fit = String(level)
        if (element.scrollWidth <= element.clientWidth) return
      }
    }
    if (typeof ResizeObserver === 'undefined') {
      fit()
      return
    }
    const observer = new ResizeObserver(fit)
    observer.observe(element.parentElement ?? element)
    return () => observer.disconnect()
  }, [content])
  return ref
}
