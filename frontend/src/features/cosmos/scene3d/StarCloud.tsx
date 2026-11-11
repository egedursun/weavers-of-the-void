import { useEffect, useMemo } from 'react'
import { useThree } from '@react-three/fiber'
import { BufferAttribute, BufferGeometry, type Raycaster } from 'three'
import { onTap } from '@/lib/sceneTap'

export type CloudStar = {
  id: number
  position: [number, number, number]
  color: [number, number, number]
}

const CLOUD_POINT_SIZE = 3

function setPointThreshold(raycaster: Raycaster, threshold: number) {
  raycaster.params.Points = { threshold }
}

export function StarCloud({
  stars,
  onPick,
  pickRadius,
}: {
  stars: readonly CloudStar[]
  onPick?: (id: number) => void
  pickRadius?: number
}) {
  const ids = useMemo(() => stars.map((star) => star.id), [stars])
  const geometry = useMemo(() => {
    const positions = new Float32Array(stars.length * 3)
    const colors = new Float32Array(stars.length * 3)
    stars.forEach((star, index) => {
      positions.set(star.position, index * 3)
      colors.set(star.color, index * 3)
    })
    const built = new BufferGeometry()
    built.setAttribute('position', new BufferAttribute(positions, 3))
    built.setAttribute('color', new BufferAttribute(colors, 3))
    return built
  }, [stars])
  useEffect(() => () => geometry.dispose(), [geometry])
  const raycaster = useThree((state) => state.raycaster)
  useEffect(() => {
    if (pickRadius !== undefined) setPointThreshold(raycaster, pickRadius)
  }, [raycaster, pickRadius])
  return (
    <points
      geometry={geometry}
      frustumCulled={false}
      onClick={
        onPick
          ? onTap((event) => {
              const id =
                event.index === undefined ? undefined : ids[event.index]
              if (id !== undefined) onPick(id)
            })
          : undefined
      }
    >
      <pointsMaterial
        vertexColors
        size={CLOUD_POINT_SIZE}
        sizeAttenuation={false}
      />
    </points>
  )
}
