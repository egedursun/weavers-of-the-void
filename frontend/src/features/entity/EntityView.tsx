import { useCallback, useMemo, useState } from 'react'
import { BookOpen, SearchX } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { OrnateFrame } from '@/components/ui/ornate'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, Section } from '@/components/domain'
import { MentionText } from '@/components/domain/MentionText'
import { Text } from '@/components/typography'
import { targetsOfRefs } from '@/features/chronicle/linkTargets'
import { CitySection } from '@/features/city/CitySection'
import { CosmicBeingSection } from '@/features/cosmography/BeingsPanel'
import { PhenomenonSection } from '@/features/cosmography/PhenomenaPanel'
import { CelestialReadingsSection } from '@/features/cosmography/ReadingsSection'
import { CommunityAddictions } from '@/features/cosmos/EconomyControls'
import { LawProfileSection } from '@/features/divine/LawProfileSection'
import { OuterProfileSection } from '@/features/divine/OuterProfileSection'
import { RegardSection } from '@/features/divine/RegardSection'
import { DedicationSection } from '@/features/foundations/DedicationSection'
import { SiteSection } from '@/features/gatherings/SiteSection'
import { Lightbox } from '@/features/images/Lightbox'
import { useImageGenEvents } from '@/features/images/imageGenState'
import {
  DressSection,
  EmblemsSection,
  MusicSection,
  SubstancesSection,
} from '@/features/kinds/CultureSections'
import {
  OrganisationKindsSection,
  RankKindsSection,
  WorkSection,
} from '@/features/kinds/SocietySections'
import { LawGrammarSection } from '@/features/lawGrammar/LawGrammarSection'
import { MadeEntitySection } from '@/features/madeKinds/KindPages'
import { MADE_ENTITY_TYPES } from '@/features/madeKinds/model'
import { OuterAgencySection } from '@/features/outerAgency/OuterAgencySection'
import { ObserverSurveySection } from '@/features/physics/SurveySection'
import { CommunityRelations } from '@/features/relations/CommunityRelations'
import { CommunityWars } from '@/features/wars/CommunityWars'
import { MilitarySection } from '@/features/wars/military/MilitarySection'
import { VesselSection } from '@/features/wars/military/VesselCard'
import { RecordActions } from './actions/RecordActions'
import { buildContext, isCommunity } from './actions/context'
import { EntityCtx } from './actions/entityContext'
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
import { EntityEconomy } from './economy/EntityEconomy'
import { NodeMaterials } from './economy/NodeMaterials'
import { PolityProduction } from './economy/PolityProduction'
import { ResourceProfile } from './economy/ResourceProfile'
import { PriceBoard, TradeRouteSection } from './economy/RouteAndMarket'
import { CommunityRoutes } from './economy/RouteControls'
import { SentientPacts } from './economy/SentientPact'
import { FactionSection } from './faction/Faction'
import { AfterlifeSection, SoulSection } from './faith/Afterlife'
import { DoctrineSection } from './faith/Doctrine'
import { PossessedSection } from './faith/Possessed'
import { EventSection } from './happenings/EventCard'
import { EventsHereSection } from './happenings/EventsHere'
import { LandShapeSection } from './happenings/LandShape'
import { EraSection } from './lore/EraSection'
import { FestivalYearSection } from './lore/FestivalYearSection'
import { LearningSection } from './lore/LearningSection'
import { LoreSection } from './lore/LoreSection'
import { isLoreKind } from './lore/model'
import { RumoursSection } from './lore/rumours/RumoursSection'
import {
  EquipmentSection,
  KinSection,
  LifeSection,
} from './mortal/MortalSections'
import { CreatePlace } from './place/CreatePlace'
import { PlaceSection } from './place/PlaceSection'
import { HouseSection, OathsSection, TreatySection } from './realm/HouseTreaty'
import { RealmSection } from './realm/Realm'
import { scrollToSection } from './scrollToSection'
import { AfflictionsSection } from './sections/AfflictionsSection'
import { ArrangeExtras } from './sections/ArrangeExtras'
import { BiographySection } from './sections/BiographySection'
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
import { EntityNote } from './sections/EntityNote'
import { EntityOpportunities } from './sections/EntityOpportunities'
import { EntityRecords } from './sections/EntityRecords'
import { EntityRelated } from './sections/EntityRelated'
import { EntityRelations } from './sections/EntityRelations'
import { EntityStats } from './sections/EntityStats'
import { EntityTimeline } from './sections/EntityTimeline'
import { HandOfGodPanel } from './sections/HandOfGodPanel'
import { KnowledgeLawPanel } from './sections/KnowledgeLawPanel'
import { MemoriesSection } from './sections/MemoriesSection'
import { MindSection } from './sections/MindSection'
import { PathFinder } from './sections/PathFinder'
import { PeopleBeliefs } from './sections/PeopleBeliefs'
import { SkillsSection } from './sections/SkillsSection'
import { SocietyEconomy } from './sections/SocietyEconomy'
import { TagEditor } from './sections/TagEditor'
import { ThingSections } from './sections/ThingSections'
import {
  CultureDriftSection,
  LoyaltySection,
  MobilitySection,
} from './society/CultureLoyalty'
import {
  DemographySection,
  LabourSection,
  PeopleProfileSection,
} from './society/Demography'
import { DiseaseSection } from './society/DiseaseCard'
import { ClassWealthSection, NeedsSection } from './society/Needs'
import {
  SettlementPlanSection,
  TreasurySection,
} from './society/SettlementPlan'
import { PeopleStructuresSection, StructureSection } from './society/Structures'
import {
  BeastSection,
  FoodWebSection,
  HerdsSection,
} from './wilds/BeastSection'
import { WildsCreateBar } from './wilds/CreateWilds'
import { RegionCropsSection } from './wilds/FloraPanels'
import { PetsSection } from './wilds/PetsSection'
import { SpeciesSection } from './wilds/SpeciesSection'
import { TotemSection } from './wilds/TotemSection'

const VAST = new Set(['cosmic_being', 'outer_being'])
const BODIED = new Set(['mortal', 'species', 'beast', ...VAST])

const MIND_TYPES = new Set([
  'mortal',
  'people',
  'settlement',
  'cult',
  'faction',
])

const CULTURED = new Set(['people', 'culture'])

const WORKING = new Set(['people', 'settlement', 'polity', 'culture'])
const RANKED = new Set([
  'people',
  'settlement',
  'polity',
  'culture',
  'cult',
  'faction',
])
const ORGANISED = new Set(['people', 'polity', 'culture', 'cult', 'faction'])

const SITE_TYPES = new Set(['place', 'structure', 'settlement', 'vessel'])
const SITE_FLAGS = new Set(['ruin', 'previous_creation'])

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
  const trading =
    entity.entity_type === 'people' || entity.entity_type === 'settlement'
  const cultured = CULTURED.has(entity.entity_type)
  const eventful =
    entity.entity_type === 'region' ||
    entity.entity_type === 'place' ||
    entity.entity_type === 'settlement'
  const sited =
    SITE_TYPES.has(entity.entity_type) ||
    detail.flags.some((flag) => SITE_FLAGS.has(flag))
  const embodied = BODIED.has(entity.entity_type)
  const made = MADE_ENTITY_TYPES.has(entity.entity_type)
  const afflictable =
    entity.entity_type === 'mortal' || entity.entity_type === 'beast'
  const maimedHome =
    entity.entity_type === 'settlement' || entity.entity_type === 'people'
  const minded = MIND_TYPES.has(entity.entity_type)
  const acts = entity.status === 'canon' && agentTypeOf(entity.entity_type)
  return (
    <EntityCtx.Provider value={ctx}>
      <article
        data-entity-page={entity.id}
        className='flex min-w-0 flex-col gap-8'
      >
        <EntityHero
          detail={detail}
          onOpenImages={() => setLightbox(0)}
          readOnlyReason={readOnly}
        />
        <OrnateFrame
          frame='card'
          crest
          className='flex min-w-0 flex-col gap-4 p-5'
        >
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
        </OrnateFrame>
        <CanonFacts ctx={ctx} readOnlyReason={readOnly} />
        <EntityStats ctx={ctx} readOnlyReason={readOnly} />
        <SocietyEconomy detail={detail} />
        {isCommunity(ctx.type) && <CommunityAddictions entityId={entity.id} />}
        <EntityRelations ctx={ctx} />
        {isCommunity(ctx.type) && entity.status === 'canon' && (
          <CommunityRelations ctx={ctx} readOnlyReason={readOnly} />
        )}
        {isCommunity(ctx.type) && <CommunityWars entityId={entity.id} />}
        {isCommunity(ctx.type) && (
          <RegardSection communityId={entity.id} readOnlyReason={readOnly} />
        )}
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
        <EntityEnvironment
          entityId={entity.id}
          entityType={entity.entity_type}
        />
        {entity.entity_type === 'place' && <PlaceSection placeId={entity.id} />}
        {entity.entity_type === 'region' && (
          <CreatePlace regionId={entity.id} />
        )}
        {entity.entity_type === 'region' && (
          <LandShapeSection regionId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'region' && (
          <RegionCropsSection regionId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'mortal' && (
          <PetsSection mortalId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'natural_law' && (
          <LawProfileSection lawId={entity.id} />
        )}
        {entity.entity_type === 'natural_law' && (
          <LawGrammarSection lawId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'outer_being' && (
          <OuterProfileSection beingId={entity.id} />
        )}
        {entity.entity_type === 'outer_being' && (
          <OuterAgencySection beingId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'phenomenon' && (
          <PhenomenonSection entityId={entity.id} />
        )}
        {entity.entity_type === 'cosmic_being' && (
          <CosmicBeingSection entityId={entity.id} />
        )}
        {made && (
          <MadeEntitySection
            entityId={entity.id}
            entityType={entity.entity_type}
            worldId={entity.world_id}
          />
        )}
        {entity.entity_type === 'celestial' && (
          <CelestialReadingsSection celestialId={entity.id} />
        )}
        {entity.entity_type === 'event' && (
          <EventSection eventId={entity.id} readOnlyReason={readOnly} />
        )}
        {sited && (
          <SiteSection
            siteId={entity.id}
            entityType={entity.entity_type}
            readOnlyReason={readOnly}
          />
        )}
        {eventful && (
          <EventsHereSection locationId={entity.id} readOnlyReason={readOnly} />
        )}
        {trading && (
          <DemographySection
            communityId={entity.id}
            readOnlyReason={readOnly}
          />
        )}
        {trading && <LabourSection communityId={entity.id} />}
        {entity.entity_type === 'people' && (
          <PeopleProfileSection
            peopleId={entity.id}
            readOnlyReason={readOnly}
          />
        )}
        {entity.entity_type === 'people' && (
          <FestivalYearSection peopleId={entity.id} readOnlyReason={readOnly} />
        )}
        {trading && (
          <NeedsSection communityId={entity.id} readOnlyReason={readOnly} />
        )}
        {trading && (
          <ClassWealthSection
            communityId={entity.id}
            readOnlyReason={readOnly}
          />
        )}
        {(entity.entity_type === 'people' ||
          entity.entity_type === 'polity') && (
          <ObserverSurveySection observerId={entity.id} />
        )}
        {entity.entity_type === 'people' && (
          <CultureDriftSection
            communityId={entity.id}
            readOnlyReason={readOnly}
          />
        )}
        {cultured && (
          <>
            <DressSection nodeId={entity.id} readOnlyReason={readOnly} />
            <EmblemsSection nodeId={entity.id} readOnlyReason={readOnly} />
            <MusicSection nodeId={entity.id} readOnlyReason={readOnly} />
            <SubstancesSection nodeId={entity.id} readOnlyReason={readOnly} />
          </>
        )}
        {WORKING.has(entity.entity_type) && (
          <WorkSection nodeId={entity.id} readOnlyReason={readOnly} />
        )}
        {RANKED.has(entity.entity_type) && (
          <RankKindsSection nodeId={entity.id} readOnlyReason={readOnly} />
        )}
        {ORGANISED.has(entity.entity_type) && (
          <OrganisationKindsSection
            nodeId={entity.id}
            readOnlyReason={readOnly}
          />
        )}
        {trading && (
          <LoyaltySection communityId={entity.id} readOnlyReason={readOnly} />
        )}
        {(trading || entity.entity_type === 'mortal') && (
          <MobilitySection
            entityId={entity.id}
            mortal={entity.entity_type === 'mortal'}
            readOnlyReason={readOnly}
          />
        )}
        {entity.entity_type === 'settlement' && (
          <CitySection settlementId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'settlement' && (
          <SettlementPlanSection
            settlementId={entity.id}
            readOnlyReason={readOnly}
          />
        )}
        {entity.entity_type === 'settlement' && (
          <TreasurySection settlementId={entity.id} />
        )}
        {entity.entity_type === 'structure' && (
          <StructureSection structureId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'people' && (
          <PeopleStructuresSection
            peopleId={entity.id}
            readOnlyReason={readOnly}
          />
        )}
        {entity.entity_type === 'disease' && (
          <DiseaseSection diseaseId={entity.id} readOnlyReason={readOnly} />
        )}
        {(trading ||
          entity.entity_type === 'polity' ||
          entity.entity_type === 'mortal') && (
          <RealmSection entityId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'house' && (
          <HouseSection houseId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'treaty' && (
          <TreatySection treatyId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'faction' && (
          <FactionSection factionId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'mortal' && (
          <OathsSection entityId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'structure' && (
          <DedicationSection
            structureId={entity.id}
            readOnlyReason={readOnly}
          />
        )}
        {entity.entity_type === 'cult' && (
          <DoctrineSection cultId={entity.id} readOnlyReason={readOnly} />
        )}
        {isLoreKind(entity.entity_type) && (
          <LoreSection
            entityId={entity.id}
            kind={entity.entity_type}
            readOnlyReason={readOnly}
          />
        )}
        {isCommunity(ctx.type) && (
          <LearningSection holderId={entity.id} readOnlyReason={readOnly} />
        )}
        {(isCommunity(ctx.type) || entity.entity_type === 'polity') && (
          <RumoursSection communityId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'polity' && (
          <EraSection polityId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'species' && (
          <SpeciesSection speciesId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'beast' && (
          <BeastSection beastId={entity.id} readOnlyReason={readOnly} />
        )}
        {isCommunity(ctx.type) && (
          <HerdsSection communityId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'region' && (
          <FoodWebSection regionId={entity.id} />
        )}
        {entity.entity_type === 'region' && !readOnly && (
          <WildsCreateBar regionId={entity.id} />
        )}
        {entity.entity_type === 'people' && (
          <TotemSection peopleId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'spirit' && (
          <SoulSection spiritId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'mortal' && (
          <PossessedSection hostId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'region' && (
          <AfterlifeSection regionId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'vessel' && (
          <VesselSection vesselId={entity.id} readOnlyReason={readOnly} />
        )}
        {(entity.entity_type === 'army' ||
          entity.entity_type === 'mortal' ||
          entity.entity_type === 'faction' ||
          isCommunity(ctx.type)) && (
          <MilitarySection
            entityId={entity.id}
            kind={entity.entity_type}
            readOnlyReason={readOnly}
          />
        )}
        {(entity.entity_type === 'people' ||
          entity.entity_type === 'settlement') && (
          <EntityEconomy
            communityId={entity.id}
            worldId={entity.world_id}
            readOnlyReason={readOnly}
          />
        )}
        {(entity.entity_type === 'people' ||
          entity.entity_type === 'settlement') && (
          <PriceBoard marketId={entity.id} />
        )}
        {(entity.entity_type === 'people' ||
          entity.entity_type === 'settlement') && (
          <CommunityRoutes communityId={entity.id} />
        )}
        {(entity.entity_type === 'item' ||
          entity.entity_type === 'structure' ||
          entity.entity_type === 'vessel' ||
          entity.entity_type === 'army') && (
          <NodeMaterials nodeId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'resource' && (
          <ResourceProfile
            resourceId={entity.id}
            worldId={entity.world_id}
            readOnlyReason={readOnly}
          />
        )}
        {entity.entity_type === 'resource' && (
          <SentientPacts resourceId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'polity' && (
          <PolityProduction polityId={entity.id} />
        )}
        {entity.entity_type === 'trade_route' && (
          <TradeRouteSection routeId={entity.id} readOnlyReason={readOnly} />
        )}
        {embodied && (
          <BodySection
            nodeId={entity.id}
            emptyNote={
              VAST.has(entity.entity_type)
                ? 'Its body forms the first time it is struck.'
                : undefined
            }
          />
        )}
        {afflictable && <AfflictionsSection nodeId={entity.id} />}
        {entity.entity_type === 'people' && (
          <PeopleBodyCustoms peopleId={entity.id} />
        )}
        {maimedHome && <CommunityMaimed communityId={entity.id} />}
        {entity.entity_type === 'mortal' && (
          <LifeSection mortalId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'mortal' && (
          <KinSection mortalId={entity.id} readOnlyReason={readOnly} />
        )}
        {entity.entity_type === 'mortal' && (
          <EquipmentSection mortalId={entity.id} readOnlyReason={readOnly} />
        )}
        {minded && <MindSection nodeId={entity.id} />}
        {entity.entity_type === 'mortal' && (
          <SkillsSection nodeId={entity.id} />
        )}
        {minded && <MemoriesSection nodeId={entity.id} />}
        <BiographySection nodeId={entity.id} readOnlyReason={readOnly} />
        <ThingSections
          nodeId={entity.id}
          kind={entity.entity_type}
          statKeys={Object.keys(entity.stats).filter((key) => key !== 'kind')}
          readOnlyReason={readOnly}
          scope={made ? 'made' : 'every'}
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
    </EntityCtx.Provider>
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
