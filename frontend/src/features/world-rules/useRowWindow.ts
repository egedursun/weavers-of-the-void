import type { RefObject } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'

type RowWindowOptions = {
  count: number
  scroller: RefObject<HTMLDivElement | null>
  estimateSize: (index: number) => number
  getItemKey: (index: number) => string
  overscan: number
}

export function useRowWindow({
  count,
  scroller,
  estimateSize,
  getItemKey,
  overscan,
}: RowWindowOptions) {
  const virtualizer = useVirtualizer({
    count,
    getScrollElement: () => scroller.current,
    estimateSize,
    overscan,
    getItemKey,
  })
  const items = virtualizer.getVirtualItems()
  const before = items.length > 0 ? items[0].start : 0
  const after =
    items.length > 0
      ? virtualizer.getTotalSize() - items[items.length - 1].end
      : 0
  return { items, before, after, measure: virtualizer.measureElement }
}
