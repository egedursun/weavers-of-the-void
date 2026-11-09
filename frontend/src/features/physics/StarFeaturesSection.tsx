import { Gem } from 'lucide-react'
import { CosmicFeaturesPanel } from './CosmicFeaturesPanel'
import { useStarPhysics } from './api'
import { QuerySection } from './parts'

export function StarFeaturesSection({ starId }: { starId: number }) {
  const query = useStarPhysics(starId)
  return (
    <QuerySection
      id='section-star-features'
      title='Around this star'
      description='Asteroid fields, comets, rogue worlds and wells that belong to its light.'
      icon={Gem}
      tone='gold'
      query={query}
    >
      {(view) => (
        <CosmicFeaturesPanel features={view.features} starId={starId} />
      )}
    </QuerySection>
  )
}
