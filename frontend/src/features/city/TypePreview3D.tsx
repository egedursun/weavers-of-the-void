import { Suspense, type ReactNode } from 'react'
import { Model } from './Model'
import { SceneFrame } from './SceneFrame'
import { type Look } from './models'

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
    <SceneFrame label={label} reach={1.2} fallback={fallback}>
      <Suspense fallback={null}>
        {look.map((part, index) => (
          <Model key={`${part.model}-${index}`} part={part} x={0} z={0} />
        ))}
      </Suspense>
    </SceneFrame>
  )
}
