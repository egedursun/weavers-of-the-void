import { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import { useLatest } from '@/features/cosmos/scene3d/useLatest'
import { type DimensionState } from './dimensionMaterial'
import { paintDimension } from './dimensionPaint'
import { type ClusterInput, paintCluster } from './scalePaint'

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

export function DimensionThumb({
  dimension,
  label,
  className,
}: {
  dimension: DimensionState
  label: string
  className?: string
}) {
  const canvas = useCanvas(dimension, paintDimension)
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
