import { useNavigate } from '@tanstack/react-router'
import {
  ArrowDownToLine,
  Bot,
  BookOpen,
  Building2,
  ChevronDown,
  Clock,
  Compass,
  Languages,
  Library,
  Map as MapIcon,
  MapPinned,
  Orbit,
  ShieldCheck,
  Star,
  Thermometer,
  TriangleAlert,
  UserRound,
  Users,
  Waves,
  Wind,
} from 'lucide-react'
import { formatCompact, formatDecimal } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  EntityLink,
  MiniStat,
  PagedList,
  Portrait,
  Section,
  StatBar,
} from '@/components/domain'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { Label, Muted, SectionTitle, Text } from '@/components/typography'
import { useCatalogue } from '@/features/entity/api/queries'
import { usePersistentState } from '@/features/map/usePersistentState'
import { mediaUrl } from '@/features/pantheon/media'
import { CreatorHandPanel } from './CreatorHandPanel'
import { DialectDetails } from './DialectDetails'
import { ForeignGodList } from './ForeignGodsPanel'
import { PaletteStrip, WorldDisc } from './Glyphs'
import { HorizonSection } from './HorizonSection'
import { RouteList } from './RouteList'
import { VoyageCard } from './VoyageCard'
import { WorldEditForm } from './WorldEditForm'
import { WorldGeography, WorldLaws } from './WorldLore'
import { WorldPulse } from './WorldPulse'
import { type CosmosWorld, type Discovery, type SonPublic } from './api'
import { type CommandSection } from './cosmosSearch'
import { type CosmosIndex, isMisty } from './model/cosmosModel'
import { type Phonology } from './model/dialect'
import {
  CLIMATE_LABEL,
  DISCOVERY_LABEL,
  STAR_TYPE_LABEL,
  ATMOSPHERE_LABEL,
  GRAVITY_LABEL,
} from './model/labels'
import { type RuleBook } from './model/rules'

const DIALECT_OPEN_KEY = 'aerona.cosmos.dialect'

const LEAK_MAX = 100

const DISCOVERY_VARIANT: Record<
  Discovery,
  'success' | 'secondary' | 'outline'
> = {
  known: 'success',
  legend: 'secondary',
  unknown: 'outline',
  forgotten: 'outline',
}

type WorldCardProps = {
  item: CosmosWorld
  index: CosmosIndex
  rules: RuleBook
  sons: SonPublic[]
  isHome: boolean
  highlightedRouteId?: number
  onSelectWorld: (worldId: number) => void
  onOpenCommand: (section: CommandSection) => void
  onDescend: (worldId: number) => void
}

function timeText(factor: number): string {
  if (factor === 1) return 'Normal flow'
  return factor < 1
    ? `Slow (×${formatDecimal(factor)})`
    : `Fast (×${formatDecimal(factor)})`
}

function DialectAccordion({
  worldId,
  phonology,
}: {
  worldId: number
  phonology: Phonology
}) {
  const [open, setOpen] = usePersistentState<boolean>(
    `${DIALECT_OPEN_KEY}.${worldId}`,
    false,
    (value) => typeof value === 'boolean'
  )
  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      data-dialect-accordion={worldId}
      className='flex min-w-0 flex-col gap-3 rounded-lg border p-3'
    >
      <CollapsibleTrigger asChild>
        <Button variant='ghost' className='justify-start'>
          <Languages />
          <span className='min-w-0 flex-1 truncate text-start'>
            Its dialect: how names are born here
          </span>
          <ChevronDown
            className={
              open ? 'rotate-180 transition-transform' : 'transition-transform'
            }
          />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <DialectDetails phonology={phonology} />
      </CollapsibleContent>
    </Collapsible>
  )
}

export function WorldCard({
  item,
  index,
  rules,
  sons,
  isHome,
  highlightedRouteId,
  onSelectWorld,
  onOpenCommand,
  onDescend,
}: WorldCardProps) {
  const navigate = useNavigate()
  const drawer = useDrawerStack()
  const deadRealm = useCatalogue().data?.world_types.find(
    (type) => type.key === item.world.world_type
  )?.realm_of_dead
  const world = item.world
  const palette = index.palette(world.world_type)
  const host = index.star(world.star_id)
  const parent = index.world(world.parent_world_id)
  const moons = index.moonsOf(world.id)
  const sonById = new Map(sons.map((son) => [son.son.id, son]))
  const sonName = (id: number) => sonById.get(id)?.son.name
  const warnAt = rules.get('leakWarning')
  const dangerAt = rules.get('leakDanger')
  const leakTone =
    dangerAt !== undefined && world.leakage >= dangerAt
      ? 'destructive'
      : warnAt !== undefined && world.leakage >= warnAt
        ? 'warning'
        : 'default'
  const twin = index.world(world.mirror_twin_id)
  const arriving = index.arrivingAt(world.id)
  const gods = index.godsOf(world.id)
  const climate = world.climate_era
    ? `${CLIMATE_LABEL[world.climate_era]}${world.climate_since_epoch !== null ? ` since epoch ${world.climate_since_epoch}` : ''}${world.climate_epochs_left ? ` (${world.climate_epochs_left} epochs left)` : ''}`
    : 'Mild, uncertain'
  return (
    <article data-world-id={world.id} className='flex min-w-0 flex-col gap-6'>
      <header className='flex min-w-0 flex-col gap-3'>
        <div className='flex min-w-0 items-center gap-3'>
          <WorldDisc
            palette={palette}
            muted={isMisty(item)}
            cover={item.cover}
          />
          <div className='flex min-w-0 flex-1 flex-col gap-1'>
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Label variant='overline' truncate>
                {item.type_label}
              </Label>
              <Badge size='sm' variant={DISCOVERY_VARIANT[world.discovery]}>
                {DISCOVERY_LABEL[world.discovery]}
              </Badge>
              {deadRealm && (
                <Badge size='sm' variant='secondary'>
                  A realm of the dead
                </Badge>
              )}
            </div>
            <SectionTitle level={3} truncate={2}>
              {world.name}
            </SectionTitle>
          </div>
        </div>
        <Muted variant='caption'>
          {host
            ? `${host.name} · ${STAR_TYPE_LABEL[host.star_type]}`
            : 'Starless'}
          {parent && (
            <>
              {' · moon of '}
              <Button
                variant='link'
                size='sm'
                onClick={() => onSelectWorld(parent.world.id)}
              >
                {parent.world.name}
              </Button>
            </>
          )}
          {moons.length > 0 && (
            <>
              {` · ${plural(moons.length, 'moon', 'moons')}: `}
              {moons.map((moon, position) => (
                <span key={moon.world.id}>
                  {position > 0 && ', '}
                  <Button
                    variant='link'
                    size='sm'
                    onClick={() => onSelectWorld(moon.world.id)}
                  >
                    {moon.world.name}
                  </Button>
                </span>
              ))}
            </>
          )}
          {world.creator_son_id !== null && (
            <>
              {' · born of '}
              <EntityLink kind='son' id={String(world.creator_son_id)}>
                {sonName(world.creator_son_id) ?? 'a son'}
              </EntityLink>
            </>
          )}
        </Muted>
        <PaletteStrip palette={palette} label={`${item.type_label} palette`} />
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button onClick={() => onDescend(world.id)}>
            <MapPinned />
            Descend to its map
          </Button>
          <Button
            variant='outline'
            onClick={() =>
              void drawer.open({ kind: 'world', id: String(world.id) })
            }
          >
            <BookOpen />
            Lore and history
          </Button>
          <Button
            variant='outline'
            onClick={() => void navigate({ href: `/atlas?world=${world.id}` })}
          >
            <Library />
            Open in Atlas
          </Button>
          <Button
            variant='outline'
            onClick={() =>
              void drawer.open({ kind: 'world-guide', id: String(world.id) })
            }
          >
            <Compass />
            Traveller's guide
          </Button>
        </div>
      </header>
      {(world.description || world.cosmology) && (
        <div className='flex min-w-0 flex-col gap-3'>
          {world.description && (
            <Text variant='prose'>{world.description}</Text>
          )}
          {world.cosmology && (
            <Text
              as='blockquote'
              variant='prose'
              tone='muted'
              italic
              className='border-l-2 border-primary pl-4'
            >
              {world.cosmology}
            </Text>
          )}
        </div>
      )}
      {world.phonology && (
        <DialectAccordion worldId={world.id} phonology={world.phonology} />
      )}
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'>
        <MiniStat
          icon={UserRound}
          tone='info'
          label='Souls'
          value={formatCompact(item.counts.population)}
        />
        <MiniStat
          icon={Users}
          tone='gold'
          label='Peoples'
          value={item.counts.peoples}
        />
        <MiniStat
          icon={Building2}
          tone='verdigris'
          label='Settlements'
          value={item.counts.settlements}
        />
        <MiniStat
          icon={MapIcon}
          tone='verdigris'
          label='Regions'
          value={item.counts.regions}
        />
        <MiniStat
          icon={Library}
          label='Living records'
          value={formatCompact(item.counts.living)}
        />
        <MiniStat
          icon={Bot}
          label='Mortal agents'
          value={world.mortal_agents === null ? 'Auto' : world.mortal_agents}
          hint={
            world.mortal_agents === null
              ? 'The number of acting communities is chosen automatically'
              : 'Communities that act on their own each epoch'
          }
        />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'>
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
          label='Time'
          value={timeText(world.time_factor)}
        />
        <MiniStat
          icon={Thermometer}
          tone='warning'
          label='Climate'
          value={climate}
        />
        <Button
          variant='outline'
          className='self-center'
          onClick={() => onOpenCommand('climate')}
        >
          <Thermometer />
          Climate cycle
        </Button>
      </div>
      <div className='flex min-w-0 flex-col gap-3'>
        <StatBar
          label='Danger'
          icon={TriangleAlert}
          value={world.danger}
          max={LEAK_MAX}
          tone='warning'
          showMax={false}
        />
        <StatBar
          label='Leakage'
          icon={Waves}
          value={world.leakage}
          max={LEAK_MAX}
          tone={leakTone}
          showMax={false}
        />
        {leakTone === 'destructive' && (
          <Text variant='caption' tone='destructive'>
            Outsiders are taking root in this world; the mortals' sanity is
            being gnawed.
          </Text>
        )}
        {leakTone === 'warning' && (
          <Text variant='caption' tone='warning'>
            Something is leaking in from outside.
          </Text>
        )}
      </div>
      {(world.epoch_star_entity_id !== null ||
        twin ||
        world.patron_son_id !== null) && (
        <div className='flex min-w-0 flex-col gap-2'>
          {world.epoch_star_entity_id !== null && (
            <div className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border border-primary p-3'>
              <Star
                aria-hidden='true'
                className='size-icon-sm shrink-0 text-primary'
              />
              <Text as='span'>{"This epoch's star: "}</Text>
              <EntityLink kind='entity' id={String(world.epoch_star_entity_id)}>
                {index.entityName(world.epoch_star_entity_id) ??
                  'the star of the epoch'}
              </EntityLink>
            </div>
          )}
          {twin && (
            <Muted>
              {'Mirror twin: '}
              <Button
                variant='link'
                size='sm'
                onClick={() => onSelectWorld(twin.world.id)}
              >
                {twin.world.name}
              </Button>
            </Muted>
          )}
          {world.patron_son_id !== null && (
            <Muted>
              <ShieldCheck
                aria-hidden='true'
                className='inline size-icon-xs text-primary'
              />{' '}
              {'Guardian: '}
              <EntityLink kind='son' id={String(world.patron_son_id)}>
                {sonName(world.patron_son_id) ?? 'a son'}
              </EntityLink>
              {world.patron_automatic
                ? ' — became guardian on its own, because most of its worshippers live here.'
                : ' — declared this world sacred.'}
            </Muted>
          )}
        </div>
      )}
      <Section title='Sons present here' level={3}>
        {item.sons.length === 0 ? (
          <Muted>No son is in this world right now.</Muted>
        ) : (
          <PagedList
            items={item.sons}
            initial={12}
            noun={['entry', 'entries']}
            as='div'
            className='flex min-w-0 flex-wrap gap-2'
            itemKey={(ref) => ref.id}
          >
            {(ref) => {
              const son = sonById.get(ref.id)
              return (
                <span
                  key={ref.id}
                  className='inline-flex min-w-0 items-center gap-2 rounded-full border py-1 pr-3 pl-1'
                >
                  <Portrait
                    name={ref.name}
                    src={mediaUrl(son?.cover)}
                    size='xs'
                    rarity={son?.son.rarity}
                  />
                  <EntityLink kind='son' id={String(ref.id)}>
                    {ref.name}
                  </EntityLink>
                </span>
              )
            }}
          </PagedList>
        )}
      </Section>
      <Section title={`Routes (${index.routesOf(world.id).length})`} level={3}>
        <RouteList
          worldId={world.id}
          index={index}
          rules={rules}
          sonName={sonName}
          highlightedRouteId={highlightedRouteId}
          onSelectWorld={onSelectWorld}
        />
      </Section>
      <HorizonSection worldId={world.id} index={index} rules={rules} />
      <WorldPulse worldId={world.id} />
      <WorldLaws worldId={world.id} />
      <WorldGeography worldId={world.id} />
      {arriving.length > 0 && (
        <Section title='Voyages coming here' level={3}>
          <div className='flex min-w-0 flex-col gap-3'>
            {arriving.map((journey) => (
              <VoyageCard key={journey.id} journey={journey} index={index} />
            ))}
          </div>
        </Section>
      )}
      {gods.length > 0 && (
        <Section title="This world's gods" level={3}>
          <ForeignGodList
            gods={gods}
            index={index}
            onSelectWorld={onSelectWorld}
          />
        </Section>
      )}
      <CreatorHandPanel item={item} isHome={isHome} rules={rules} />
      <Collapsible className='flex min-w-0 flex-col gap-4 rounded-xl border p-4'>
        <CollapsibleTrigger asChild>
          <Button variant='ghost' className='justify-start'>
            <BookOpen />
            Edit the world: name, type, physics, orbit and story
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <WorldEditForm
            key={world.id}
            item={item}
            index={index}
            rules={rules}
            sons={sons}
            isHome={isHome}
          />
        </CollapsibleContent>
      </Collapsible>
    </article>
  )
}
