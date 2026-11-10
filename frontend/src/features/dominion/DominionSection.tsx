import { Crown } from 'lucide-react'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { Muted } from '@/components/typography'
import { useNames } from '@/features/entity/api/queries'
import { GodDominionPanel } from './GodDominionPanel'
import { PlaceDominionPanel, SiteForm, ThroneForm } from './PlaceDominionPanel'
import { WorldDominionPanel } from './WorldDominionPanel'
import { useGodDominion, usePlaceDominion, useWorldDominion } from './api'
import { PLACE_TYPES } from './model'

const GODS = new Set(['son', 'foreign_god', 'creator'])

function Failed({ message }: { message: string }) {
  return (
    <EmptyState
      icon={Crown}
      size='inline'
      title='The dominion could not be read'
      description={message}
    />
  )
}

function PlaceBody({
  nodeId,
  blocked,
}: {
  nodeId: number
  blocked: string | null
}) {
  const query = usePlaceDominion(nodeId)
  const names = useNames()
  const type = names.data?.find(
    (entry) => entry.kind === 'entity' && entry.id === nodeId
  )?.type
  if (query.isPending)
    return <LoadingBlock label='Reading who rules this land' />
  if (query.isError) return <Failed message={query.error.message} />
  return (
    <PlaceDominionPanel
      data={query.data}
      blocked={blocked}
      laysSites={type !== undefined && PLACE_TYPES.includes(type)}
    />
  )
}

function WorldBody({
  nodeId,
  blocked,
}: {
  nodeId: number
  blocked: string | null
}) {
  const query = useWorldDominion(nodeId)
  if (query.isPending)
    return <LoadingBlock label='Reading who rules this world' />
  if (query.isError) return <Failed message={query.error.message} />
  return <WorldDominionPanel data={query.data} blocked={blocked} />
}

function HeavensBody({ blocked }: { blocked: string | null }) {
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Muted variant='caption'>
        Dominion lies over the regions of worlds, so a star, a galaxy, a cluster
        or a dimension holds none of its own; raise thrones and lay magic sites
        on any world from here.
      </Muted>
      <ThroneForm placeId={null} thrones={[]} blocked={blocked} />
      <SiteForm placeId={null} blocked={blocked} />
    </div>
  )
}

export function DominionSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useGodDominion(nodeId)
  const kind = query.data?.node.kind
  return (
    <Section
      id='section-dominion'
      title='Dominion'
      description='The presence of the gods over the land: dominion and its scales, design, the image peoples hold, miracles, divine creatures, thrones of power and magic sites.'
      icon={Crown}
      tone='gold'
    >
      <div
        data-surface='DominionSection'
        className='flex min-w-0 flex-col gap-3'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the dominion' />
        ) : query.isError ? (
          <Failed message={query.error.message} />
        ) : kind !== undefined && GODS.has(kind) ? (
          <GodDominionPanel data={query.data} blocked={readOnlyReason} />
        ) : kind === 'world' ? (
          <WorldBody nodeId={nodeId} blocked={readOnlyReason} />
        ) : kind === 'entity' ? (
          <PlaceBody nodeId={nodeId} blocked={readOnlyReason} />
        ) : (
          <HeavensBody blocked={readOnlyReason} />
        )}
      </div>
    </Section>
  )
}
