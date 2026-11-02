import { useCallback, useState } from 'react'

export type ShowMoreState<T> = {
  visible: readonly T[]
  total: number
  hidden: number
  initial: number
  step: number
  expanded: boolean
  more: () => void
  all: () => void
  less: () => void
}

export function useShowMore<T>(
  items: readonly T[],
  initial: number,
  step: number = initial
): ShowMoreState<T> {
  const [limit, setLimit] = useState(initial)
  const count = items.length
  const more = useCallback(() => setLimit((current) => current + step), [step])
  const all = useCallback(
    () => setLimit(Math.max(count, initial)),
    [count, initial]
  )
  const less = useCallback(() => setLimit(initial), [initial])
  const visible = count > limit ? items.slice(0, limit) : items
  return {
    visible,
    total: count,
    hidden: count - visible.length,
    initial,
    step,
    expanded: limit > initial,
    more,
    all,
    less,
  }
}
