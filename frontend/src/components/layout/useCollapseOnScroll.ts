import { useEffect, useRef, useState } from 'react'
import {
  HEADER_COLLAPSE_QUERY,
  HEADER_COLLAPSE_SCROLL_PX,
} from '@/constants/ui'
import { useMediaQuery } from '@/hooks/useMediaQuery'

export function nextCollapsed(
  previous: boolean,
  lastY: number,
  y: number,
  threshold: number
): boolean {
  if (y <= threshold) return false
  if (y > lastY) return true
  if (y < lastY) return false
  return previous
}

export function useCollapseOnScroll(
  threshold = HEADER_COLLAPSE_SCROLL_PX,
  query = HEADER_COLLAPSE_QUERY
): boolean {
  const narrow = useMediaQuery(query)
  const [collapsed, setCollapsed] = useState(false)
  const lastY = useRef(0)
  useEffect(() => {
    if (!narrow) return
    lastY.current = window.scrollY
    const onScroll = () => {
      const y = window.scrollY
      setCollapsed((previous) =>
        nextCollapsed(previous, lastY.current, y, threshold)
      )
      lastY.current = y
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [narrow, threshold])
  return narrow && collapsed
}
