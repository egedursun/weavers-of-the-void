import { useEffect, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Vector3 } from 'three'
import { cn } from '@/lib/utils'
import { Text } from '@/components/typography'
import { type LabelElements } from './labelElements'

export type { LabelElements }

export type SceneLabel = {
  key: string
  position: [number, number, number]
  text: string
  detail?: string
  strong?: boolean
  quiet?: boolean
}

const point = new Vector3()
const EDGE = 4

type Box = { left: number; right: number; top: number; bottom: number }

type Measured = { text: string; width: number; height: number }

function overlaps(a: Box, b: Box): boolean {
  return (
    a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom
  )
}

export function LabelProjector({
  labels,
  elements,
}: {
  labels: readonly SceneLabel[]
  elements: LabelElements
}) {
  const camera = useThree((state) => state.camera)
  const size = useThree((state) => state.size)
  const measured = useRef(new WeakMap<HTMLElement, Measured>())
  const written = useRef(new WeakMap<HTMLElement, string>())
  const last = useRef({ view: '', labels: labels })
  useEffect(() => {
    let live = true
    void document.fonts.ready.then(() => {
      if (!live) return
      measured.current = new WeakMap()
      last.current = { view: '', labels: last.current.labels }
    })
    return () => {
      live = false
    }
  }, [])
  useFrame(() => {
    const view = `${camera.matrixWorld.elements.join(',')}|${camera.projectionMatrix.elements.join(',')}|${size.width}x${size.height}|${elements.current.size}`
    if (view === last.current.view && labels === last.current.labels) return
    last.current = { view, labels }
    const ordered = [...labels].sort(
      (a, b) => Number(b.strong === true) - Number(a.strong === true)
    )
    const sized = ordered.flatMap((label) => {
      const element = elements.current.get(label.key)
      if (!element) return []
      const text = `${label.text}|${label.detail ?? ''}|${label.strong === true}`
      let known = measured.current.get(element)
      if (!known || known.text !== text) {
        known = {
          text,
          width: element.offsetWidth,
          height: element.offsetHeight,
        }
        measured.current.set(element, known)
      }
      return [{ label, element, known }]
    })
    const placed: Box[] = []
    for (const { label, element, known } of sized) {
      point.set(...label.position).project(camera)
      const behind = point.z > 1 || point.z < -1
      const half = known.width / 2 + EDGE
      const x = Math.min(
        Math.max(((point.x + 1) / 2) * size.width, half),
        Math.max(size.width - half, half)
      )
      const y = Math.min(
        Math.max(((1 - point.y) / 2) * size.height, known.height + EDGE),
        size.height - EDGE
      )
      const box: Box = {
        left: x - half,
        right: x + half,
        top: y - known.height - EDGE,
        bottom: y + EDGE,
      }
      const clear = !behind && !placed.some((other) => overlaps(other, box))
      if (clear) placed.push(box)
      const style = `${clear ? '1' : '0'}|${x.toFixed(1)}|${y.toFixed(1)}`
      if (written.current.get(element) === style) continue
      written.current.set(element, style)
      element.style.opacity = clear ? '1' : '0'
      element.style.transform = `translate(-50%, -100%) translate(${x}px, ${y}px)`
    }
  })
  return null
}

export function LabelLayer({
  labels,
  elements,
}: {
  labels: readonly SceneLabel[]
  elements: LabelElements
}) {
  return (
    <div
      aria-hidden='true'
      className='pointer-events-none absolute inset-0 overflow-hidden'
    >
      {labels.map((label) => (
        <span
          key={label.key}
          ref={(element) => {
            if (element) elements.current.set(label.key, element)
            else elements.current.delete(label.key)
          }}
          className={cn(
            'absolute top-0 left-0 flex flex-col items-center rounded-md px-1.5 py-0.5 text-center whitespace-nowrap opacity-0 shadow-sm',
            label.quiet
              ? 'text-cosmos-label-muted'
              : 'bg-cosmos-void/80 text-cosmos-label'
          )}
        >
          <Text
            as='span'
            variant='caption'
            weight={label.strong ? 'semibold' : 'medium'}
            tone='inherit'
          >
            {label.text}
          </Text>
          {label.detail && (
            <span className='text-cosmos-label-muted'>
              <Text as='span' variant='caption' tone='inherit'>
                {label.detail}
              </Text>
            </span>
          )}
        </span>
      ))}
    </div>
  )
}
