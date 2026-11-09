import { Pickaxe, Zap } from 'lucide-react'
import { ImpactsPanel } from './ImpactsPanel'
import { TerraformPanel } from './TerraformPanel'
import { useWorldPhysics } from './api'
import { QuerySection } from './parts'

export function WorldImpactsSection({ worldId }: { worldId: number }) {
  const query = useWorldPhysics(worldId)
  return (
    <QuerySection
      id='section-world-impacts'
      title='Bodies from the sky'
      description='Bodies that fell or are falling on this world, and when; foreseen ones can be turned aside.'
      icon={Zap}
      tone='danger'
      query={query}
    >
      {(view) => (
        <ImpactsPanel
          worldId={worldId}
          impacts={view.impacts}
          epoch={view.epoch}
        />
      )}
    </QuerySection>
  )
}

export function WorldTerraformSection({ worldId }: { worldId: number }) {
  const query = useWorldPhysics(worldId)
  return (
    <QuerySection
      id='section-world-terraform'
      title='Reshaping the world'
      description='Works that move its air, warmth, water or face a little each epoch.'
      icon={Pickaxe}
      tone='verdigris'
      query={query}
    >
      {(view) => (
        <TerraformPanel worldId={worldId} projects={view.terraforming} />
      )}
    </QuerySection>
  )
}
