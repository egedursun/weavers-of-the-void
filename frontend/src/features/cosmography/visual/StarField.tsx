import { useEffect, useMemo } from 'react'
import { BufferAttribute, BufferGeometry } from 'three'
import { seededRandom } from '@/lib/hash'
import { DUST_TOKENS } from '@/features/cosmos/model/looks'
import { shaderMaterial, uniform } from '@/features/cosmos/scene3d/materials'
import {
  DUST_FRAGMENT,
  DUST_VERTEX,
} from '@/features/cosmos/scene3d/shaders/sky'
import { useTicking } from './clock'
import { scenePalette } from './palette'

const FIELD_SEED = 4242
const POINT_RATIO = 1.3

export function StarField({
  radius,
  count = 4200,
}: {
  radius: number
  count?: number
}) {
  const geometry = useMemo(() => {
    const random = seededRandom(FIELD_SEED)
    const palette = DUST_TOKENS.map((token) => scenePalette(token))
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    const sizes = new Float32Array(count)
    const seeds = new Float32Array(count)
    for (let index = 0; index < count; index += 1) {
      const theta = random() * Math.PI * 2
      const cosPhi = random() * 2 - 1
      const sinPhi = Math.sqrt(1 - cosPhi * cosPhi)
      const distance = radius * (0.75 + random() * 0.25)
      positions.set(
        [
          Math.cos(theta) * sinPhi * distance,
          cosPhi * distance,
          Math.sin(theta) * sinPhi * distance,
        ],
        index * 3
      )
      const color = palette[Math.floor(random() * palette.length)]
      const glow = Math.pow(random(), 3) * 1.2 + 0.15
      colors.set([color[0] * glow, color[1] * glow, color[2] * glow], index * 3)
      sizes[index] = 1 + Math.pow(random(), 6) * 2.6
      seeds[index] = random()
    }
    const built = new BufferGeometry()
    built.setAttribute('position', new BufferAttribute(positions, 3))
    built.setAttribute('aColor', new BufferAttribute(colors, 3))
    built.setAttribute('aSize', new BufferAttribute(sizes, 1))
    built.setAttribute('aSeed', new BufferAttribute(seeds, 1))
    return built
  }, [radius, count])
  const material = useMemo(
    () =>
      shaderMaterial({
        vertex: DUST_VERTEX,
        fragment: DUST_FRAGMENT,
        uniforms: {
          uTime: uniform(0),
          uRatio: uniform(POINT_RATIO),
          uAttenuate: uniform(0),
        },
        blend: 'additive',
      }),
    []
  )
  useEffect(() => () => geometry.dispose(), [geometry])
  useEffect(() => () => material.dispose(), [material])
  useTicking(material)
  return <points geometry={geometry} material={material} />
}
