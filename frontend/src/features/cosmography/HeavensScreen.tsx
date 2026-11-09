import {
  Crown,
  Eye,
  Layers,
  Orbit,
  Sparkles,
  Star,
  Workflow,
} from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  PageHeader,
  Section,
} from '@/components/domain'
import { ApocalypseVariantPanel } from './ApocalypseVariantPanel'
import { DimensionAtlas, GalaxyAtlas } from './Atlases'
import { BeingsPanel } from './BeingsPanel'
import {
  CreateClusterForm,
  CreateDimensionForm,
  CreateGalaxyForm,
} from './CreateForms'
import { EventsPanel } from './EventsPanel'
import { PhenomenaPanel } from './PhenomenaPanel'
import { RiftsPanel } from './RiftsPanel'
import { ScaleTree } from './ScaleTree'
import { useCosmography, useCosmographyCatalog } from './api'
import { ladderOf } from './ladder'

export function HeavensScreen() {
  const view = useCosmography()
  const catalog = useCosmographyCatalog()
  if (view.isPending) return <LoadingBlock label='Reading the heavens' />
  if (view.isError)
    return (
      <Alert variant='destructive'>
        <Orbit />
        <AlertTitle>The heavens could not be read</AlertTitle>
        <AlertDescription>{view.error.message}</AlertDescription>
      </Alert>
    )
  const data = view.data
  const ladder = ladderOf(data)
  const placed = data.placements.filter((row) => row.star_id !== null).length
  const openRifts = data.rifts.filter((row) =>
    ['opening', 'open', 'closing'].includes(row.state)
  ).length
  return (
    <div
      data-surface='CosmographyScreen'
      className='flex min-w-0 flex-col gap-6'
    >
      <PageHeader
        eyebrow={`Epoch ${data.epoch}`}
        title='The Heavens'
        icon={Orbit}
        description='Dimensions, clusters, galaxies and the beings, rifts and wonders between them. Every value here is yours to shape or hold.'
      />
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-7'>
        <KpiTile
          label='Dimensions'
          value={data.dimensions.length}
          icon={Layers}
          tone='info'
        />
        <KpiTile
          label='Clusters'
          value={data.clusters.length}
          icon={Workflow}
          tone='verdigris'
        />
        <KpiTile
          label='Galaxies'
          value={data.galaxies.length}
          icon={Orbit}
          tone='gold'
        />
        <KpiTile
          label='Worlds under a star'
          value={placed}
          icon={Star}
          tone='gold'
        />
        <KpiTile
          label='Open rifts'
          value={openRifts}
          icon={Eye}
          tone='danger'
          harmful
        />
        <KpiTile
          label='Cosmic beings'
          value={data.beings.length}
          icon={Crown}
          tone='warning'
        />
        <KpiTile
          label='Phenomena'
          value={data.phenomena.length}
          icon={Sparkles}
          tone='info'
        />
      </div>
      <ApocalypseVariantPanel
        current={data.apocalypse_variant ?? null}
        likely={data.likely_variant}
        catalog={catalog.data}
      />
      <Section
        id='cosmography-ladder'
        title='The scale of the cosmos'
        description='Each dimension holds its clusters and galaxies; open any of them to shape it.'
        icon={Layers}
        tone='info'
      >
        {data.dimensions.length === 0 ? (
          <EmptyState
            icon={Layers}
            title='The cosmos has not been laid out yet'
            description='The first epoch lays the prime dimension, a home group and a home galaxy around the existing stars; you can bring a dimension into being now.'
          />
        ) : (
          <ScaleTree ladder={ladder} catalog={catalog.data} />
        )}
        <div className='grid min-w-0 grid-cols-1 gap-3 xl:grid-cols-3'>
          <CreateDimensionForm ladder={ladder} catalog={catalog.data} />
          <CreateClusterForm ladder={ladder} catalog={catalog.data} />
          <CreateGalaxyForm ladder={ladder} catalog={catalog.data} />
        </div>
      </Section>
      <DimensionAtlas ladder={ladder} catalog={catalog.data} />
      <GalaxyAtlas ladder={ladder} catalog={catalog.data} />
      <EventsPanel ladder={ladder} catalog={catalog.data} />
      <RiftsPanel ladder={ladder} />
      <BeingsPanel ladder={ladder} catalog={catalog.data} />
      <PhenomenaPanel data={data} catalog={catalog.data} />
    </div>
  )
}
