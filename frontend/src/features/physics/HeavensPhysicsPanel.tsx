import { Gem, Pickaxe, Zap } from 'lucide-react'
import { CosmicFeaturesPanel } from './CosmicFeaturesPanel'
import { ImpactsPanel } from './ImpactsPanel'
import { TerraformPanel } from './TerraformPanel'
import { useHeavensPhysics } from './api'
import { QuerySection } from './parts'

export function HeavensPhysicsPanel() {
  const query = useHeavensPhysics()
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <QuerySection
        id='section-heavens-features'
        title='Features of the heavens'
        description='Every asteroid field, wormhole, comet, rogue world and gravity well.'
        icon={Gem}
        tone='gold'
        query={query}
      >
        {(view) => <CosmicFeaturesPanel features={view.features} />}
      </QuerySection>
      <QuerySection
        id='section-heavens-impacts'
        title='Impacts'
        description='Every body that fell or is falling on a world.'
        icon={Zap}
        tone='danger'
        query={query}
      >
        {(view) => (
          <ImpactsPanel
            worldId={null}
            impacts={view.impacts}
            epoch={view.epoch}
          />
        )}
      </QuerySection>
      <QuerySection
        id='section-heavens-terraform'
        title='Terraforming'
        description='Every work that reshapes a world.'
        icon={Pickaxe}
        tone='verdigris'
        query={query}
      >
        {(view) => (
          <TerraformPanel worldId={null} projects={view.terraforming} />
        )}
      </QuerySection>
    </div>
  )
}
