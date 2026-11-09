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

export function LabelProjector({
  labels,
  elements,
}: {
  labels: readonly SceneLabel[]
  elements: LabelElements
}) {
  const camera = useThree((state) => state.camera)
  const size = useThree((state) => state.size)
  useFrame(() => {
    for (const label of labels) {
      const element = elements.current.get(label.key)
      if (!element) continue
      point.set(...label.position).project(camera)
      const hidden = point.z > 1 || point.z < -1
      element.style.opacity = hidden ? '0' : '1'
      const half = element.offsetWidth / 2 + EDGE
      const x = Math.min(
        Math.max(((point.x + 1) / 2) * size.width, half),
        Math.max(size.width - half, half)
      )
      const y = Math.min(
        Math.max(
          ((1 - point.y) / 2) * size.height,
          element.offsetHeight + EDGE
        ),
        size.height - EDGE
      )
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
