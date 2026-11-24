import {
  CloudSun,
  ArrowDownToLine,
  Building2,
  Clock,
  Crown,
  Ghost,
  Globe2,
  Library,
  Map as MapIcon,
  Orbit,
  Route,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Star,
  Thermometer,
  TriangleAlert,
  UserRound,
  Users,
  Waves,
  Wind,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatCompact, formatDecimal } from '@/lib/format'
import { plural } from '@/lib/units'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EmptyState,
  EntityLink,
  HeroFrame,
  MiniStat,
  Paged,
  PagedList,
  Portrait,
  Section,
} from '@/components/domain'
import { RecordNavLink } from '@/components/domain/RecordNavLink'
import { type EntryPageProps } from '@/components/layout/entry/EntryWindow'
import { Label, Muted, PageTitle, Text } from '@/components/typography'
import { CosmosAgrarianSection } from '@/features/agrarian/CosmosAgrarianSection'
import { ChronicleEntry } from '@/features/chronicle/ChronicleEntry'
import { OlderLinesButton } from '@/features/chronicle/OlderLinesButton'
import {
  type ChronicleScope,
  useChronicleKindLabels,
  useOlderLines,
} from '@/features/chronicle/api'
import { WorldPlacementSection } from '@/features/cosmography/HeavenlyLife'
import { RiftsForWorld } from '@/features/cosmography/RiftsPanel'
import { EncountersSection } from '@/features/cosmos/EncountersSection'
import { PaletteStrip, WorldDisc } from '@/features/cosmos/Glyphs'
import { useCosmos } from '@/features/cosmos/api'
import {
  ATMOSPHERE_LABEL,
  CLIMATE_LABEL,
  DISCOVERY_LABEL,
  GRAVITY_LABEL,
  SKY_EVENT_LABEL,
  TRAVEL_METHOD_LABEL,
} from '@/features/cosmos/model/labels'
import { CosmosCyclesSection } from '@/features/cycles/CosmosCyclesSection'
import { WorldDivinityPanel } from '@/features/divine/WorldDivinityPanel'
import { WorldEraSection } from '@/features/entity/lore/EraSection'
import { ThingSections } from '@/features/entity/sections/ThingSections'
import { WorldLifeSection } from '@/features/entity/wilds/FloraPanels'
import { GoldenAgeSection } from '@/features/foundations/GoldenAgeCard'
import { StorytellerSection } from '@/features/gatherings/StorytellerSection'
import { PortraitGenerateOverlay } from '@/features/images/PortraitGenerateOverlay'
import { RecordGallery } from '@/features/pantheon/RecordGallery'
import { mediaUrl } from '@/features/pantheon/media'
import { LifeClassSection } from '@/features/physics/LifeClassSection'
import { WorldSurveySection } from '@/features/physics/SurveySection'
import { WorldPhysicsSection } from '@/features/physics/WorldPhysicsSection'
import {
  WorldImpactsSection,
  WorldTerraformSection,
} from '@/features/physics/WorldShapingSection'
import { CosmosRegimeSection } from '@/features/regime/CosmosRegimeSection'
import { CelestialDepthSection } from './CelestialDepthSection'
import { WorldSeasonsSection } from './WorldSeasonsSection'
import { type WorldWiki, useWorldWiki } from './api'

const LEAK_MAX = 100

function WorldHero({ wiki }: { wiki: WorldWiki }) {
  const cosmos = useCosmos()
  const world = wiki.world
  const palette =
    cosmos.data?.world_types.find(
      (item) => item.world_type === world.world_type
    )?.palette.biome_colours ?? []
  return (
    <HeroFrame>
      <header className='flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start'>
        <PortraitGenerateOverlay
          nodeId={world.id}
          name={world.name}
          cover={wiki.cover ?? null}
          placeholder={
            <div className='flex size-portrait-xl shrink-0 items-center justify-center rounded-md border surface-sheen border-gild/60 bg-card'>
              <WorldDisc palette={palette} />
            </div>
          }
        />
        <div className='flex min-w-0 flex-1 flex-col gap-2'>
          <Label variant='overline'>{`World · ${wiki.type_label}`}</Label>
          <PageTitle truncate={2}>{world.name}</PageTitle>
          {world.description && <Muted>{world.description}</Muted>}
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Badge size='sm' variant='info'>
              <Globe2 />
              {DISCOVERY_LABEL[world.discovery]}
            </Badge>
            {world.climate_era && (
              <Badge size='sm' variant='warning'>
                <Thermometer />
                {CLIMATE_LABEL[world.climate_era]}
              </Badge>
            )}
            {wiki.star && (
              <Badge size='sm' variant='outline'>
                <Star />
                <EntityLink kind='star' id={String(wiki.star.id)}>
                  {wiki.star.name}
                </EntityLink>
              </Badge>
            )}
            {wiki.patron && (
              <Badge size='sm' variant='default'>
                <ShieldCheck />
                <EntityLink kind='son' id={String(wiki.patron.id)}>
                  {wiki.patron.name}
                </EntityLink>
              </Badge>
            )}
          </div>
          {palette.length > 0 && (
            <PaletteStrip
              palette={palette}
              label={`${wiki.type_label} palette`}
            />
          )}
          <div className='flex min-w-0 flex-wrap gap-2'>
            <RecordNavLink to={{ view: 'world-map', world: world.id }} />
            <RecordNavLink to={{ view: 'chronicle', world: world.id }} />
            <Button variant='outline' size='sm' asChild>
              <a href='#section-seasons'>
                <CloudSun />
                Climate and seasons
              </a>
            </Button>
            <EntityLink kind='world-guide' id={String(world.id)}>
              Traveller's guide
            </EntityLink>
          </div>
        </div>
      </header>
    </HeroFrame>
  )
}

function WorldSpecs({ wiki }: { wiki: WorldWiki }) {
  const world = wiki.world
  const counts = wiki.counts
  return (
    <Section id='section-world-glance' title='At a glance'>
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'>
        <MiniStat
          icon={UserRound}
          tone='info'
          label='Souls'
          value={formatCompact(counts.population)}
        />
        <MiniStat
          icon={Users}
          tone='gold'
          label='Peoples'
          value={counts.peoples}
        />
        <MiniStat
          icon={Building2}
          tone='verdigris'
          label='Settlements'
          value={counts.settlements}
        />
        <MiniStat
          icon={MapIcon}
          tone='verdigris'
          label='Regions'
          value={counts.regions}
        />
        <MiniStat
          icon={Library}
          label='Living records'
          value={formatCompact(counts.living)}
        />
        <MiniStat
          icon={Route}
          tone='info'
          label='Routes'
          value={wiki.routes.length}
        />
        <MiniStat
          icon={Orbit}
          label='Orbit'
          value={`${formatDecimal(world.orbit)} units`}
        />
        <MiniStat
          icon={ArrowDownToLine}
          label='Gravity'
          value={GRAVITY_LABEL[world.gravity]}
        />
        <MiniStat
          icon={Wind}
          label='Atmosphere'
          value={ATMOSPHERE_LABEL[world.atmosphere]}
        />
        <MiniStat
          icon={Clock}
          label='Time flows'
          value={`×${formatDecimal(world.time_factor)}`}
        />
        <MiniStat
          icon={TriangleAlert}
          tone={world.danger > LEAK_MAX / 2 ? 'danger' : 'warning'}
          label='Danger'
          value={world.danger}
        />
        <MiniStat
          icon={Waves}
          tone={world.leakage > 0 ? 'danger' : 'muted'}
          label='Leakage'
          value={world.leakage}
        />
      </div>
    </Section>
  )
}

function WorldPeoples({ wiki }: { wiki: WorldWiki }) {
  if (
    wiki.peoples.length === 0 &&
    wiki.sons.length === 0 &&
    wiki.foreign_gods.length === 0
  )
    return null
  return (
    <Section id='section-world-peoples' title='Who lives and reigns here'>
      {wiki.peoples.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>{`Greatest peoples · ${wiki.counts.peoples}`}</Label>
          <PagedList
            items={wiki.peoples}
            initial={8}
            noun={['people', 'peoples']}
            className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'
            itemKey={(item) => item.entity.id}
          >
            {(item) => (
              <li className='flex min-w-0 items-center gap-3 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
                <Portrait
                  name={item.entity.name}
                  src={mediaUrl(item.cover)}
                  size='sm'
                />
                <span className='flex min-w-0 flex-1 flex-col'>
                  <EntityLink kind='entity' id={String(item.entity.id)}>
                    {item.entity.name}
                  </EntityLink>
                  <Muted variant='caption'>{`${plural(item.population, 'soul', 'souls')}`}</Muted>
                </span>
              </li>
            )}
          </PagedList>
        </div>
      )}
      {(wiki.sons.length > 0 || wiki.foreign_gods.length > 0) && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Paged items={wiki.sons}>
            {(son) => (
              <Badge key={son.id} size='sm' variant='default'>
                <Crown />
                <EntityLink kind='son' id={String(son.id)}>
                  {son.name}
                </EntityLink>
              </Badge>
            )}
          </Paged>
          <Paged items={wiki.foreign_gods}>
            {(god) => (
              <Badge key={god.id} size='sm' variant='outline'>
                <Ghost />
                <EntityLink kind='foreign-god' id={String(god.id)}>
                  {god.name}
                </EntityLink>
              </Badge>
            )}
          </Paged>
        </div>
      )}
    </Section>
  )
}

function WorldSky({ wiki }: { wiki: WorldWiki }) {
  const cosmos = useCosmos()
  const worldName = (id: number) =>
    cosmos.data?.worlds.find((item) => item.world.id === id)?.world.name ??
    'another world'
  if (wiki.routes.length === 0 && wiki.sky_events.length === 0) return null
  return (
    <Section id='section-world-roads' title='Roads and skies'>
      {wiki.routes.length > 0 && (
        <PagedList
          items={wiki.routes}
          initial={6}
          noun={['route', 'routes']}
          className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'
          itemKey={(route) => route.id}
        >
          {(route) => {
            const other =
              route.world_a_id === wiki.world.id
                ? route.world_b_id
                : route.world_a_id
            return (
              <li className='flex min-w-0 items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
                <Route
                  aria-hidden='true'
                  className='size-icon-sm shrink-0 text-info'
                />
                <span className='min-w-0 flex-1 truncate'>
                  <EntityLink kind='world' id={String(other)}>
                    {worldName(other)}
                  </EntityLink>
                </span>
                <Badge size='sm' variant='outline'>
                  {TRAVEL_METHOD_LABEL[route.method]}
                </Badge>
              </li>
            )
          }}
        </PagedList>
      )}
      {wiki.sky_events.length > 0 && (
        <PagedList
          items={wiki.sky_events}
          initial={5}
          noun={['sky event', 'sky events']}
          className='flex min-w-0 flex-col gap-1.5'
          itemKey={(event) => event.id}
        >
          {(event) => (
            <li className='flex min-w-0 items-start gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
              <Sparkles
                aria-hidden='true'
                className='size-icon-sm shrink-0 text-primary'
              />
              <span className='flex min-w-0 flex-1 flex-col'>
                <Text as='span' weight='medium'>
                  {SKY_EVENT_LABEL[event.kind]}
                </Text>
                {event.text && <Muted variant='caption'>{event.text}</Muted>}
              </span>
              <Badge
                size='sm'
                variant='outline'
              >{`Epoch ${event.epoch}`}</Badge>
            </li>
          )}
        </PagedList>
      )}
    </Section>
  )
}

export function CelestialTimeline({
  lines,
  total,
  scope,
  scopeId,
  emptyText,
}: {
  lines: WorldWiki['timeline']
  total: number
  scope: ChronicleScope
  scopeId: number
  emptyText: string
}) {
  const labels = useChronicleKindLabels()
  const older = useOlderLines(scope, scopeId, lines.length, total)
  const known = [...lines, ...older.lines].sort((a, b) => b.id - a.id)
  return (
    <Section
      id='section-world-chronicle'
      title='Chronicle'
      description='The lines written about it, newest first.'
    >
      {known.length === 0 ? (
        <EmptyState
          icon={ScrollText}
          size='compact'
          title='No chronicle yet'
          description={emptyText}
        />
      ) : (
        <div className='flex min-w-0 flex-col gap-2'>
          <PagedList
            items={known}
            initial={10}
            noun={['entry', 'entries']}
            as='ol'
            className='flex min-w-0 flex-col gap-1'
            itemKey={(line) => line.id}
          >
            {(line) => (
              <ChronicleEntry
                line={line}
                kindLabel={labels.get(line.kind)}
                editable={false}
              />
            )}
          </PagedList>
          <OlderLinesButton older={older} />
        </div>
      )}
    </Section>
  )
}

export function WorldWikiView({ worldId }: { worldId: number }) {
  const wiki = useWorldWiki(worldId)
  if (wiki.isPending)
    return (
      <div className='flex flex-col gap-4'>
        <Skeleton className='h-control-lg w-2/3' />
        <Skeleton className='h-textarea w-full' />
      </div>
    )
  if (wiki.isError)
    return (
      <Alert variant='destructive'>
        <Globe2 />
        <AlertTitle>This world could not be read</AlertTitle>
        <AlertDescription>{wiki.error.message}</AlertDescription>
      </Alert>
    )
  const data = wiki.data
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <WorldHero wiki={data} />
      {data.world.cosmology && (
        <Section id='section-world-origin' title='How it began'>
          <Text
            as='blockquote'
            variant='prose'
            italic
            className='border-l-2 border-primary pl-4'
          >
            {data.world.cosmology}
          </Text>
        </Section>
      )}
      <WorldSpecs wiki={data} />
      <WorldSeasonsSection worldId={data.world.id} />
      <GoldenAgeSection worldId={data.world.id} />
      <WorldEraSection worldId={data.world.id} />
      <WorldLifeSection worldId={data.world.id} />
      <EncountersSection worldId={data.world.id} />
      <WorldPlacementSection world={data.world} />
      <WorldPhysicsSection worldId={data.world.id} />
      <LifeClassSection worldId={data.world.id} />
      <WorldImpactsSection worldId={data.world.id} />
      <WorldTerraformSection worldId={data.world.id} />
      <WorldSurveySection worldId={data.world.id} />
      <RiftsForWorld worldId={data.world.id} />
      <StorytellerSection worldId={data.world.id} />
      <CosmosCyclesSection />
      <CosmosRegimeSection />
      <CosmosAgrarianSection />
      <CelestialDepthSection
        kind='world'
        id={data.world.id}
        name={data.world.name}
        depth={data.depth ?? null}
      />
      <WorldPeoples wiki={data} />
      <WorldSky wiki={data} />
      <CelestialTimeline
        lines={data.timeline}
        total={data.timeline_total}
        scope='world'
        scopeId={data.world.id}
        emptyText='Nothing has been written about this world yet.'
      />
      <RecordGallery
        sectionId='section-world-images'
        title='Images of the world'
        nodeId={data.world.id}
        name={data.world.name}
        images={data.images}
        prompt={data.world.image_prompt ?? null}
        promptLabel='Image prompt'
        onSavePrompt={(prompt) =>
          unwrap(
            api.PATCH('/api/worlds/{world_id}', {
              params: { path: { world_id: data.world.id } },
              body: { image_prompt: prompt, automatic_mortal_agents: false },
            })
          )
        }
      />
      <WorldDivinityPanel worldId={data.world.id} />
      <ThingSections nodeId={data.world.id} kind='world' />
    </div>
  )
}

export function WorldWikiPage({ id }: EntryPageProps) {
  const worldId = Number(id)
  if (!Number.isInteger(worldId) || worldId <= 0)
    return (
      <EmptyState
        icon={Globe2}
        title='No such world'
        description='This link does not point to a world.'
      />
    )
  return <WorldWikiView worldId={worldId} />
}
