import { useRef, useState } from 'react'
import { Html } from '@react-three/drei'
import { useFrame, useThree } from '@react-three/fiber'
import { Vector3 } from 'three'
import { cn } from '@/lib/utils'
import { Text } from '@/components/typography'
import { Dot } from './ZoneDot'

export type SceneLabel = {
  id: string
  x: number
  z: number
  text: string
  fill: string
  rank: number
  chosen: boolean
}

const HEIGHT = 1.5
const CHAR_WIDTH = 7
const PADDING = 34
const LINE = 26

type Box = readonly [number, number, number, number]

function overlaps(first: Box, second: Box): boolean {
  return (
    first[0] < second[2] &&
    second[0] < first[2] &&
    first[1] < second[3] &&
    second[1] < first[3]
  )
}

function sameIds(first: ReadonlySet<string>, second: ReadonlySet<string>) {
  return first.size === second.size && [...first].every((id) => second.has(id))
}

export function SceneLabels({ labels }: { labels: SceneLabel[] }) {
  const { camera, size } = useThree()
  const [shown, setShown] = useState<ReadonlySet<string>>(new Set())
  const point = useRef(new Vector3())
  const seen = useRef('')
  useFrame(() => {
    const view = `${camera.matrixWorld.elements.map((value) => value.toFixed(2)).join(',')}|${size.width}x${size.height}|${labels.map((label) => `${label.id}${label.chosen ? '*' : ''}`).join(',')}`
    if (view === seen.current) return
    seen.current = view
    const taken: Box[] = []
    const next = new Set<string>()
    const ordered = [...labels].sort(
      (first, second) =>
        Number(second.chosen) - Number(first.chosen) ||
        Number(shown.has(second.id)) - Number(shown.has(first.id)) ||
        second.rank - first.rank
    )
    for (const label of ordered) {
      point.current.set(label.x, HEIGHT, label.z).project(camera)
      if (point.current.z > 1) continue
      const x = ((point.current.x + 1) / 2) * size.width
      const y = ((1 - point.current.y) / 2) * size.height
      if (x < 0 || y < 0 || x > size.width || y > size.height) continue
      const half = (label.text.length * CHAR_WIDTH + PADDING) / 2
      const box: Box = [x - half, y - LINE / 2, x + half, y + LINE / 2]
      if (!label.chosen && taken.some((other) => overlaps(other, box))) continue
      taken.push(box)
      next.add(label.id)
    }
    if (!sameIds(next, shown)) setShown(next)
  })
  return (
    <>
      {labels
        .filter((label) => shown.has(label.id))
        .map((label) => (
          <Html
            key={label.id}
            position={[label.x, HEIGHT, label.z]}
            center
            zIndexRange={[10, 0]}
          >
            <div
              className={cn(
                'pointer-events-none flex items-center gap-1.5 rounded-full border bg-popover/90 px-2 py-0.5 whitespace-nowrap text-popover-foreground shadow-sm backdrop-blur-sm',
                label.chosen && 'border-primary'
              )}
            >
              <Dot fill={label.fill} />
              <Text as='span' variant='caption' tone='inherit'>
                {label.text}
              </Text>
            </div>
          </Html>
        ))}
    </>
  )
}
