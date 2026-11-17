import { type RefObject, useLayoutEffect } from 'react'

export function useFitLines(target: RefObject<HTMLElement | null>) {
  useLayoutEffect(() => {
    const node = target.current
    if (!node) return
    const fit = () => {
      const line = Number.parseFloat(getComputedStyle(node).lineHeight)
      if (!Number.isFinite(line) || line <= 0) return
      const lines = Math.max(1, Math.floor((node.clientHeight + 1) / line))
      node.style.setProperty('--lines', String(lines))
    }
    fit()
    const observer = new ResizeObserver(fit)
    observer.observe(node)
    return () => observer.disconnect()
  }, [target])
}
