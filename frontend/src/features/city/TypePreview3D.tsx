import { Suspense, type ReactNode } from 'react'
import { Model } from './Model'
import { SceneFrame } from './SceneFrame'
import { GROUND_TILE, type Look } from './models'

export default function TypePreview3D({
  look,
  label,
  fallback,
}: {
  look: Look
  label: string
  fallback: ReactNode
}) {
  return (
    <SceneFrame label={label} reach={1.3} fallback={fallback}>
      <Suspense fallback={null}>
        <Model part={{ model: GROUND_TILE }} x={0} z={0} y={-0.06} />
        {look.map((part, index) => (
          <Model key={`${part.model}-${index}`} part={part} x={0} z={0} />
        ))}
      </Suspense>
    </SceneFrame>
  )
}
