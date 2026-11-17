import { type PointerEvent, type RefObject, useCallback } from 'react'

const TILT_DEGREES = 14
const PERCENT = 100

export function useCardTilt(
  target: RefObject<HTMLDivElement | null>,
  enabled: boolean
) {
  const reset = useCallback(() => {
    const node = target.current
    if (!node) return
    node.removeAttribute('data-tilting')
    for (const name of ['--tilt-x', '--tilt-y', '--glare-x', '--glare-y'])
      node.style.removeProperty(name)
    node.style.setProperty('--glare-o', '0')
  }, [target])

  const onPointerMove = useCallback(
    (event: PointerEvent<HTMLElement>) => {
      const node = target.current
      if (!enabled || !node || event.pointerType === 'touch') return
      const box = event.currentTarget.getBoundingClientRect()
      if (box.width === 0 || box.height === 0) return
      const x = (event.clientX - box.left) / box.width
      const y = (event.clientY - box.top) / box.height
      node.setAttribute('data-tilting', '')
      node.style.setProperty('--tilt-x', `${(x - 0.5) * TILT_DEGREES}deg`)
      node.style.setProperty('--tilt-y', `${(0.5 - y) * TILT_DEGREES}deg`)
      node.style.setProperty('--glare-x', `${x * PERCENT}%`)
      node.style.setProperty('--glare-y', `${y * PERCENT}%`)
      node.style.setProperty('--glare-o', '1')
    },
    [enabled, target]
  )

  return { onPointerMove, onPointerLeave: reset }
}
