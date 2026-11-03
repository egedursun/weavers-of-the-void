import { useCallback, useMemo, useState } from 'react'
import { BookOpen, SearchX } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, Section } from '@/components/domain'
import { MentionText } from '@/components/domain/MentionText'
import { Text } from '@/components/typography'
import { targetsOfRefs } from '@/features/chronicle/linkTargets'
import { CommunityAddictions } from '@/features/cosmos/EconomyControls'
import { Lightbox } from '@/features/images/Lightbox'
import { useImageGenEvents } from '@/features/images/imageGenState'
import { CommunityRelations } from '@/features/relations/CommunityRelations'
import { CommunityWars } from '@/features/wars/CommunityWars'
import { RecordActions } from './actions/RecordActions'
import { buildContext, isCommunity } from './actions/context'
import { READ_ONLY_REASON } from './actions/gate'
import { agentTypeOf } from './agentTypes'
import {
  useCatalogue,
  useEntity,
  useEntityBonds,
  useWorldState,
} from './api/queries'
import { type EntityDetail } from './api/types'
import { RELATION_PAGE_MAX } from './constants'
import { scrollToSection } from './scrollToSection'
import { ArrangeExtras } from './sections/ArrangeExtras'
import { BodySection } from './sections/BodySection'
import { CommunityMaimed, PeopleBodyCustoms } from './sections/BodySociety'
import { CanonFacts } from './sections/CanonFacts'
import { DangerZone } from './sections/DangerZone'
import { EntityAgentContext } from './sections/EntityAgentContext'
import { EntityBonds } from './sections/EntityBonds'
import { EntityChronicle } from './sections/EntityChronicle'
import { EntityDepth } from './sections/EntityDepth'
import { EntityDreams } from './sections/EntityDreams'
import { EntityEditForm } from './sections/EntityEditForm'
import { EntityEnvironment } from './sections/EntityEnvironment'
import { EntityHero } from './sections/EntityHero'
import { EntityImages } from './sections/EntityImages'
import { EntityMechanics } from './sections/EntityMechanics'
import { EntityNote } from './sections/EntityNote'
import { EntityOpportunities } from './sections/EntityOpportunities'
import { EntityRecords } from './sections/EntityRecords'
import { EntityRelated } from './sections/EntityRelated'
import { EntityRelations } from './sections/EntityRelations'
import { EntityStats } from './sections/EntityStats'
import { EntityTimeline } from './sections/EntityTimeline'
import { HandOfGodPanel } from './sections/HandOfGodPanel'
import { KnowledgeLawPanel } from './sections/KnowledgeLawPanel'
import { PathFinder } from './sections/PathFinder'
import { PeopleBeliefs } from './sections/PeopleBeliefs'
import { SocietyEconomy } from './sections/SocietyEconomy'
import { TagEditor } from './sections/TagEditor'

const SECTION_LINKS = [
  { id: 'section-facts', label: 'Facts' },
  { id: 'section-stats', label: 'Stats' },
  { id: 'section-society', label: 'Society' },
  { id: 'section-depth', label: 'Depth' },
  { id: 'section-opportunities', label: 'Opportunities' },
  { id: 'section-hand', label: 'Hand of God' },
  { id: 'section-commands', label: 'Commands' },
  { id: 'section-community-relations', label: 'Community relations' },
  { id: 'section-wars', label: 'Wars' },
  { id: 'section-bonds', label: 'Bonds' },
  { id: 'section-path', label: 'Connections' },
  { id: 'section-images', label: 'Images' },
  { id: 'section-chronicle', label: 'Chronicle' },
  { id: 'section-environment', label: 'Environment' },
  { id: 'section-body', label: 'Body' },
  { id: 'section-body-customs', label: 'Wounds and bodies' },
  { id: 'section-maimed', label: 'The maimed' },
  { id: 'section-mechanics', label: 'Mechanics' },
  { id: 'section-edit', label: 'Edit' },
]

function SectionNav({ present }: { present: Set<string> }) {
  const links = SECTION_LINKS.filter((link) => present.has(link.id))
  if (links.length < 4) return null
  return (
    <nav aria-label='Sections' className='flex min-w-0 flex-wrap gap-1'>
      {links.map((link) => (
        <Button
          key={link.id}
          variant='ghost'
          size='sm'
          onClick={() => scrollToSection(link.id)}
        >
          {link.label}
        </Button>
      ))}
    </nav>
  )
}

function EntityBody({ detail }: { detail: EntityDetail }) {
  const state = useWorldState()
  const catalogue = useCatalogue()
  const needsAll = detail.bond_total > detail.bonds.length
  const allBonds = useEntityBonds(
    detail.entity.id,
    0,
    RELATION_PAGE_MAX,
    needsAll
  )
  const bonds = needsAll ? (allBonds.data?.items ?? detail.bonds) : detail.bonds
  const ctx = useMemo(
    () =>
      buildContext(
        detail,
        bonds,
        state.data,
        catalogue.data?.entity_types ?? []
      ),
    [detail, bonds, state.data, catalogue.data]
  )
  const [lightbox, setLightbox] = useState<number | null>(null)
  const [highlight, setHighlight] = useState<number | null>(null)
  const readOnly = state.data?.read_only ? READ_ONLY_REASON : null
  const entity = detail.entity
  const targets = useMemo(
    () =>
      targetsOfRefs([
        ...detail.breadcrumb,
        ...bonds.map((bond) => bond.other),
        ...detail.contents.map((item) => ({
          id: item.id,
          kind: 'entity' as const,
          name: item.name,
        })),
      ]),
    [detail, bonds]
  )
  const pick = useCallback((epoch: number) => {
    setHighlight(epoch)
    scrollToSection('section-chronicle')
  }, [])
  const present = new Set(SECTION_LINKS.map((link) => link.id))
  if (!detail.insight.society) present.delete('section-society')
  if (entity.entity_type !== 'region' && entity.entity_type !== 'place')
    present.delete('section-environment')
  const embodied =
    entity.entity_type === 'mortal' || entity.entity_type === 'species'
  if (!embodied) present.delete('section-body')
  if (entity.entity_type !== 'people') present.delete('section-body-customs')
  const maimedHome =
    entity.entity_type === 'settlement' || entity.entity_type === 'people'
  if (!maimedHome) present.delete('section-maimed')
  const acts = entity.status === 'canon' && agentTypeOf(entity.entity_type)
  if (!acts) present.delete('section-opportunities')
  if (!isCommunity(ctx.type)) {
    present.delete('section-community-relations')
    present.delete('section-wars')
  }
  return (
    <article
      data-entity-page={entity.id}
      className='flex min-w-0 flex-col gap-8'
    >
      <EntityHero
        detail={detail}
        onOpenImages={() => setLightbox(0)}
        readOnlyReason={readOnly}
      />
      <SectionNav present={present} />
      <EntityTimeline
        lines={detail.chronicle}
        birthEpoch={entity.birth_epoch}
        currentEpoch={state.data?.world?.epoch ?? entity.birth_epoch}
        onPick={pick}
      />
      {entity.fate_note && (
        <blockquote className='flex min-w-0 flex-col gap-1 border-s-2 border-primary ps-4'>
          <Text weight='semibold'>Fate</Text>
          <Text italic>{entity.fate_note}</Text>
        </blockquote>
      )}
      {entity.description && (
        <Text variant='prose'>
          <MentionText
            text={entity.description}
            targets={targets}
            selfId={entity.id}
          />
        </Text>
      )}
      <CanonFacts ctx={ctx} readOnlyReason={readOnly} />
      <EntityStats ctx={ctx} readOnlyReason={readOnly} />
      <SocietyEconomy detail={detail} />
      {isCommunity(ctx.type) && <CommunityAddictions entityId={entity.id} />}
      <EntityRelations ctx={ctx} />
      {isCommunity(ctx.type) && entity.status === 'canon' && (
        <CommunityRelations ctx={ctx} readOnlyReason={readOnly} />
      )}
      {isCommunity(ctx.type) && <CommunityWars entityId={entity.id} />}
      <EntityDepth entity={entity} targets={targets} />
      <KnowledgeLawPanel ctx={ctx} readOnlyReason={readOnly} />
      <PeopleBeliefs ctx={ctx} readOnlyReason={readOnly} />
      {acts && <EntityOpportunities entityId={entity.id} />}
      <HandOfGodPanel ctx={ctx} />
      <Section
        id='section-commands'
        title="God's commands"
        description='Everything you can order for this record. Each command shows its live cost.'
      >
        <ArrangeExtras ctx={ctx} readOnlyReason={readOnly} />
        <TagEditor ctx={ctx} readOnlyReason={readOnly} />
        <RecordActions ctx={ctx} />
      </Section>
      {acts && <EntityAgentContext entityId={entity.id} name={entity.name} />}
      <EntityDreams entityId={entity.id} />
      <EntityRecords ctx={ctx} />
      <EntityBonds ctx={ctx} readOnlyReason={readOnly} />
      <EntityRelated similar={detail.similar} />
      <PathFinder fromId={entity.id} fromName={entity.name} />
      <EntityNote
        key={entity.id}
        entityId={entity.id}
        note={entity.private_note}
        readOnlyReason={readOnly}
      />
      <EntityImages
        detail={detail}
        onOpen={setLightbox}
        readOnlyReason={readOnly}
      />
      <EntityChronicle
        entityId={entity.id}
        total={detail.chronicle_total}
        highlightEpoch={highlight}
      />
      <EntityEnvironment entityId={entity.id} entityType={entity.entity_type} />
      {embodied && <BodySection nodeId={entity.id} />}
      {entity.entity_type === 'people' && (
        <PeopleBodyCustoms peopleId={entity.id} />
      )}
      {maimedHome && <CommunityMaimed communityId={entity.id} />}
      <EntityMechanics
        nodeId={entity.id}
        statKeys={Object.keys(entity.stats).filter((key) => key !== 'kind')}
        readOnlyReason={readOnly}
      />
      <EntityEditForm
        key={`${entity.id}-${entity.name}-${entity.description.length}`}
        entity={entity}
        readOnlyReason={readOnly}
      />
      <DangerZone ctx={ctx} readOnlyReason={readOnly} />
      <Lightbox
        images={detail.images}
        index={lightbox}
        onIndexChange={setLightbox}
        title={entity.name}
        veiled={entity.entity_type === 'outer_being'}
        readOnlyReason={readOnly}
      />
    </article>
  )
}

export function EntityViewSkeleton() {
  return (
    <div className='flex min-w-0 flex-col gap-4' aria-busy='true'>
      <div className='flex min-w-0 gap-4'>
        <Skeleton className='size-portrait-xl rounded-lg' />
        <div className='flex min-w-0 flex-1 flex-col gap-2'>
          <Skeleton className='h-control-md w-1/3' />
          <Skeleton className='h-control-lg w-2/3' />
          <Skeleton className='h-control-sm w-1/2' />
        </div>
      </div>
      <Skeleton className='h-textarea w-full' />
      <Skeleton className='h-textarea w-full' />
    </div>
  )
}

export function EntityView({ id }: { id: number | null }) {
  useImageGenEvents()
  const query = useEntity(id)
  if (id === null || !Number.isInteger(id) || id <= 0)
    return (
      <EmptyState
        icon={SearchX}
        title='No such record'
        description='The link does not point at a record of this world.'
      />
    )
  if (query.isPending) return <EntityViewSkeleton />
  if (query.isError)
    return (
      <EmptyState
        icon={BookOpen}
        title='This record cannot be opened'
        description={query.error.message}
        action={
          <Button variant='outline' onClick={() => void query.refetch()}>
            Try again
          </Button>
        }
      />
    )
  return <EntityBody detail={query.data} />
}
