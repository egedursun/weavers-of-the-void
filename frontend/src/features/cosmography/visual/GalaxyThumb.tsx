import { useEffect, useRef } from 'react'
import { unitHash } from '@/lib/hash'
import { cn } from '@/lib/utils'
import { useLatest } from '@/features/cosmos/scene3d/useLatest'
import { type FormInput, GALAXY_LOOK, type GalaxyShape } from './galaxyForm'
import { type ThumbStar, paintGalaxy } from './galaxyPaint'

const THUMB_POINTS = 5200
const MIN_TILT = 0.35
const TILT_RANGE = 0.5

export type { ThumbStar }

type GalaxyThumbProps = {
  galaxy: FormInput
  shape: GalaxyShape
  label: string
  stars?: readonly ThumbStar[]
  tilt?: number
  points?: number
  className?: string
}

export function GalaxyThumb({
  galaxy,
  shape,
  label,
  stars = [],
  tilt,
  points = THUMB_POINTS,
  className,
}: GalaxyThumbProps) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const angle =
    tilt ??
    GALAXY_LOOK[galaxy.galaxy_type].view ??
    MIN_TILT + unitHash(`galaxy-tilt-${galaxy.id}`) * TILT_RANGE
  const signature = JSON.stringify([galaxy, stars, angle, shape, points])
  const latest = useLatest({ galaxy, shape, stars, angle, points })
  useEffect(() => {
    const element = canvas.current
    if (!element) return
    let visible = false
    let painted = ''
    const render = () => {
      if (!visible) return
      const size = `${element.clientWidth}x${element.clientHeight}`
      if (size === painted) return
      painted = size
      const now = latest.current
      paintGalaxy(
        element,
        now.galaxy,
        now.shape,
        now.stars,
        now.angle,
        now.points
      )
    }
    const sizes = new ResizeObserver(render)
    const sight = new IntersectionObserver((entries) => {
      visible = entries.some((entry) => entry.isIntersecting)
      render()
    })
    sizes.observe(element)
    sight.observe(element)
    return () => {
      sizes.disconnect()
      sight.disconnect()
    }
  }, [signature, latest])
  return (
    <canvas
      ref={canvas}
      role='img'
      aria-label={label}
      className={cn('block rounded-xl bg-cosmos-void', className)}
    />
  )
}
