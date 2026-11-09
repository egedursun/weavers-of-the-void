import { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import { useLatest } from '@/features/cosmos/scene3d/useLatest'
import {
  type ClusterInput,
  type SigilInput,
  paintCluster,
  paintSigil,
} from './scalePaint'

function useCanvas<T>(
  value: T,
  paint: (canvas: HTMLCanvasElement, value: T) => void
) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const latest = useLatest(value)
  const signature = JSON.stringify(value)
  useEffect(() => {
    const element = canvas.current
    if (!element) return
    const render = () => paint(element, latest.current)
    render()
    const observer = new ResizeObserver(render)
    observer.observe(element)
    return () => observer.disconnect()
  }, [signature, latest, paint])
  return canvas
}

export function DimensionSigil({
  dimension,
  label,
  className,
}: {
  dimension: SigilInput
  label: string
  className?: string
}) {
  const canvas = useCanvas(dimension, paintSigil)
  return (
    <canvas
      ref={canvas}
      role='img'
      aria-label={label}
      className={cn('block rounded-xl bg-cosmos-void', className)}
    />
  )
}

export function ClusterThumb({
  cluster,
  label,
  className,
}: {
  cluster: ClusterInput
  label: string
  className?: string
}) {
  const canvas = useCanvas(cluster, paintCluster)
  return (
    <canvas
      ref={canvas}
      role='img'
      aria-label={label}
      className={cn('block rounded-xl bg-cosmos-void', className)}
    />
  )
}
